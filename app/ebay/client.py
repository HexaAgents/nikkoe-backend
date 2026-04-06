from __future__ import annotations

import base64
from datetime import datetime, timezone
from urllib.parse import quote

import httpx

from app.config import settings

SANDBOX_AUTH_URL = "https://auth.sandbox.ebay.com/oauth2/authorize"
PRODUCTION_AUTH_URL = "https://auth.ebay.com/oauth2/authorize"

SANDBOX_TOKEN_URL = "https://api.sandbox.ebay.com/identity/v1/oauth2/token"
PRODUCTION_TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"

SANDBOX_API_URL = "https://api.sandbox.ebay.com"
PRODUCTION_API_URL = "https://api.ebay.com"

SCOPES = [
    "https://api.ebay.com/oauth/api_scope",
    "https://api.ebay.com/oauth/api_scope/sell.fulfillment.readonly",
]


def _is_sandbox() -> bool:
    return settings.EBAY_ENVIRONMENT.upper() == "SANDBOX"


def _auth_url() -> str:
    return SANDBOX_AUTH_URL if _is_sandbox() else PRODUCTION_AUTH_URL


def _token_url() -> str:
    return SANDBOX_TOKEN_URL if _is_sandbox() else PRODUCTION_TOKEN_URL


def _api_url() -> str:
    return SANDBOX_API_URL if _is_sandbox() else PRODUCTION_API_URL


def _basic_auth_header() -> str:
    credentials = f"{settings.EBAY_CLIENT_ID}:{settings.EBAY_CLIENT_SECRET}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded}"


def get_consent_url() -> str:
    scope_str = quote(" ".join(SCOPES))
    ru_name = quote(settings.EBAY_RU_NAME)
    return (
        f"{_auth_url()}"
        f"?client_id={quote(settings.EBAY_CLIENT_ID)}"
        f"&response_type=code"
        f"&redirect_uri={ru_name}"
        f"&scope={scope_str}"
    )


def exchange_code_for_token(code: str) -> dict:
    """Exchange an authorization code for access + refresh tokens."""
    resp = httpx.post(
        _token_url(),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": _basic_auth_header(),
        },
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.EBAY_RU_NAME,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return {
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token", ""),
        "expires_in": data["expires_in"],
    }


def refresh_access_token(refresh_token: str) -> dict:
    """Use a refresh token to obtain a new access token."""
    resp = httpx.post(
        _token_url(),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": _basic_auth_header(),
        },
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "scope": " ".join(SCOPES),
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return {
        "access_token": data["access_token"],
        "expires_in": data["expires_in"],
    }


def get_orders(
    access_token: str,
    date_from: str | None = None,
    limit: int = 200,
    offset: int = 0,
) -> dict:
    """Fetch orders from the eBay Fulfillment API."""
    filters = []
    if date_from:
        filters.append(f"creationdate:[{date_from}..]")

    params: dict[str, str | int] = {"limit": limit, "offset": offset}
    if filters:
        params["filter"] = ",".join(filters)

    resp = httpx.get(
        f"{_api_url()}/sell/fulfillment/v1/order",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        params=params,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def get_all_orders(
    access_token: str,
    date_from: str | None = None,
) -> list[dict]:
    """Fetch all orders, handling pagination automatically."""
    all_orders: list[dict] = []
    offset = 0
    limit = 200

    while True:
        data = get_orders(access_token, date_from=date_from, limit=limit, offset=offset)
        orders = data.get("orders", [])
        all_orders.extend(orders)

        total = data.get("total", 0)
        if offset + limit >= total or not orders:
            break
        offset += limit

    return all_orders


def get_valid_access_token(token_repo) -> str | None:
    """Get a valid access token, refreshing if expired. Returns None if no token stored."""
    stored = token_repo.get_current()
    if not stored:
        return None

    now = datetime.now(timezone.utc)
    expiry = stored.get("token_expiry")
    if isinstance(expiry, str):
        expiry = datetime.fromisoformat(expiry)

    if expiry and expiry > now:
        return stored["access_token"]

    result = refresh_access_token(stored["refresh_token"])
    token_repo.update_access_token(
        stored["id"],
        result["access_token"],
        result["expires_in"],
    )
    return result["access_token"]
