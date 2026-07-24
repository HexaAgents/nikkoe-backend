import asyncio
from dataclasses import dataclass

from cachetools import TTLCache
from fastapi import HTTPException, Request

from app.dependencies import supabase, supabase_auth
from app.repositories.base import _is_transient

_auth_cache: TTLCache = TTLCache(maxsize=128, ttl=60)
_AUTH_RETRIES = 2


@dataclass
class UserProfile:
    user_id: int
    first_name: str
    last_name: str
    email: str | None


@dataclass
class CurrentUser:
    id: str
    email: str | None
    profile: UserProfile | None


async def get_current_user(request: Request) -> CurrentUser:
    auth_header = request.headers.get("authorization", "")
    token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else ""

    if not token:
        return _unauthorized("Missing authorization token")

    cached = _auth_cache.get(token)
    if cached is not None:
        return cached

    for attempt in range(_AUTH_RETRIES + 1):
        try:
            user_response = supabase_auth.auth.get_user(token)
            break
        except Exception as exc:
            if not _is_transient(exc):
                return _unauthorized("Invalid or expired token")
            if attempt == _AUTH_RETRIES:
                raise HTTPException(
                    status_code=503, detail="Authentication service is temporarily unavailable"
                ) from exc
            await asyncio.sleep(0.25 * (attempt + 1))

    user = user_response.user
    if not user:
        return _unauthorized("Invalid or expired token")

    try:
        profile_response = (
            supabase.table("user")
            .select("id, first_name, last_name, email")
            .eq("auth_id", user.id)
            .maybe_single()
            .execute()
        )
    except Exception:
        profile_response = None

    profile = None
    if profile_response and profile_response.data:
        p = profile_response.data
        profile = UserProfile(
            user_id=p["id"],
            first_name=p["first_name"],
            last_name=p.get("last_name", ""),
            email=p.get("email"),
        )

    current_user = CurrentUser(id=user.id, email=user.email, profile=profile)
    _auth_cache[token] = current_user
    return current_user


def _unauthorized(message: str):
    raise HTTPException(status_code=401, detail=message)
