from fastapi import APIRouter, Depends

from app.dependencies import supabase
from app.errors import AppError
from app.middleware.auth import CurrentUser, get_current_user
from app.schemas import ChangePasswordInput, LoginInput, SignupInput

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
def login(body: LoginInput):
    try:
        response = supabase.auth.sign_in_with_password({"email": body.email, "password": body.password})
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
        response = supabase.auth.sign_up({"email": body.email, "password": body.password})
    except Exception as e:
        raise AppError(400, str(e))

    user = response.user
    if not user:
        raise AppError(400, "Signup failed")

    session_data = None
    if response.session:
        session_data = {
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
            "expires_in": response.session.expires_in,
            "token_type": response.session.token_type,
        }

    return {
        "user": {"id": user.id, "email": user.email},
        "session": session_data,
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
    try:
        supabase.auth.sign_in_with_password({"email": user.email or "", "password": body.current_password})
    except Exception:
        raise AppError(400, "Current password is incorrect")

    try:
        supabase.auth.admin.update_user_by_id(user.id, {"password": body.new_password})
    except Exception as e:
        raise AppError(400, str(e))

    return {"success": True}
