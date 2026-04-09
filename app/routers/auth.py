import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.config import settings
from app.dependencies import supabase_auth
from app.errors import AppError
from app.middleware.auth import CurrentUser, get_current_user
from app.schemas import ChangePasswordInput, LoginInput, SignupInput


class RefreshInput(BaseModel):
    refresh_token: str


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
def login(body: LoginInput):
    try:
        response = supabase_auth.auth.sign_in_with_password({"email": body.email, "password": body.password})
    except Exception as e:
        raise AppError(401, str(e))

    user = response.user
    session = response.session

    if not user or not session:
        raise AppError(401, "Invalid email or password")

    return {
        "user": {"id": user.id, "email": user.email},
        "session": {
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "expires_in": session.expires_in,
            "token_type": session.token_type,
        },
    }


@router.post("/signup")
def signup(body: SignupInput):
    try:
        admin_resp = supabase_auth.auth.admin.create_user(
            {"email": body.email, "password": body.password, "email_confirm": True}
        )
    except Exception as e:
        raise AppError(400, str(e))

    user = admin_resp.user
    if not user:
        raise AppError(400, "Signup failed")

    try:
        login_resp = supabase_auth.auth.sign_in_with_password({"email": body.email, "password": body.password})
    except Exception:
        return {"user": {"id": user.id, "email": user.email}, "session": None}

    session_data = None
    if login_resp.session:
        session_data = {
            "access_token": login_resp.session.access_token,
            "refresh_token": login_resp.session.refresh_token,
            "expires_in": login_resp.session.expires_in,
            "token_type": login_resp.session.token_type,
        }

    return {
        "user": {"id": user.id, "email": user.email},
        "session": session_data,
    }


@router.post("/refresh")
def refresh_token(body: RefreshInput):
    resp = httpx.post(
        f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=refresh_token",
        json={"refresh_token": body.refresh_token},
        headers={"apikey": settings.SUPABASE_ANON_KEY},
    )

    if resp.status_code != 200:
        raise AppError(401, "Session expired — please log in again")

    data = resp.json()
    return {
        "session": {
            "access_token": data["access_token"],
            "refresh_token": data["refresh_token"],
            "expires_in": data["expires_in"],
            "token_type": data.get("token_type", "bearer"),
        },
    }


@router.get("/me")
def get_me(user: CurrentUser = Depends(get_current_user)):
    return {
        "user": {"id": user.id, "email": user.email},
        "profile": (
            {
                "user_id": user.profile.user_id,
                "name": f"{user.profile.first_name} {user.profile.last_name}".strip(),
                "email_address": user.profile.email,
            }
            if user.profile
            else None
        ),
    }


@router.post("/change-password")
def change_password(body: ChangePasswordInput, user: CurrentUser = Depends(get_current_user)):
    # Verify current password via direct GoTrue REST call (bypasses SDK quirks).
    verify_resp = httpx.post(
        f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=password",
        json={"email": user.email, "password": body.current_password},
        headers={"apikey": settings.SUPABASE_ANON_KEY},
    )
    if verify_resp.status_code != 200:
        raise AppError(400, "Current password is incorrect")

    # Update password via GoTrue admin endpoint.
    update_resp = httpx.put(
        f"{settings.SUPABASE_URL}/auth/v1/admin/users/{user.id}",
        json={"password": body.new_password},
        headers={
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        },
    )
    if update_resp.status_code != 200:
        detail = update_resp.json().get("msg", "Failed to update password")
        raise AppError(400, detail)

    return {"success": True}
