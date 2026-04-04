import dataclasses

from fastapi import APIRouter, Depends

from app.middleware.auth import CurrentUser, get_current_user
from app.repositories.user import UserRepository
from app.schemas import CreateUserInput
from app.services.user import UserService

repo = UserRepository()
service = UserService(repo)
router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me")
def get_me(user: CurrentUser = Depends(get_current_user)):
    profile = service.get_profile(user.profile)
    return dataclasses.asdict(profile)


@router.post("/", status_code=201)
def create_user(body: CreateUserInput, user: CurrentUser = Depends(get_current_user)):
    result = service.create_user(body.email, body.password)
    return {"user": result}
