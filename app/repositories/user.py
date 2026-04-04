from app.dependencies import supabase


class UserRepository:
    def create_auth_user(self, email: str, password: str) -> dict:
        response = supabase.auth.admin.create_user(
            {"email": email, "password": password, "email_confirm": True}
        )
        return {"id": response.user.id, "email": response.user.email}
