from app.errors import NotFoundError
from app.repositories.user import UserRepository


class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    def get_profile(self, profile):
        if profile is None:
            raise NotFoundError("User profile", "current")
        return profile

    def create_user(self, email: str, password: str):
        return self.repo.create_auth_user(email, password)
