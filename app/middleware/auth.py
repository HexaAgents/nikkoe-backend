from dataclasses import dataclass

from fastapi import Request

from app.dependencies import supabase


@dataclass
class UserProfile:
    user_id: str
    name: str
    email_address: str | None


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

    try:
        user_response = supabase.auth.get_user(token)
    except Exception:
        return _unauthorized("Invalid or expired token")

    user = user_response.user
    if not user:
        return _unauthorized("Invalid or expired token")

    profile_response = (
        supabase.table("users").select("user_id, name, email_address").eq("auth_id", user.id).maybe_single().execute()
    )

    profile = None
    if profile_response.data:
        p = profile_response.data
        profile = UserProfile(
            user_id=p["user_id"],
            name=p["name"],
            email_address=p.get("email_address"),
        )

    return CurrentUser(id=user.id, email=user.email, profile=profile)


def _unauthorized(message: str):
    from fastapi import HTTPException

    raise HTTPException(status_code=401, detail=message)
