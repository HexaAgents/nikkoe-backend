from fastapi import APIRouter, Depends, Query

from app.middleware.auth import CurrentUser, get_current_user
from app.repositories.category import CategoryRepository
from app.schemas import CategoryInput
from app.services.category import CategoryService

repo = CategoryRepository()
service = CategoryService(repo)
router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("/")
def list_categories(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: CurrentUser = Depends(get_current_user),
):
    return service.list_categories(limit, offset)


@router.post("/", status_code=201)
def create_category(body: CategoryInput, user: CurrentUser = Depends(get_current_user)):
    return service.create_category(body.model_dump())


@router.delete("/{category_id}")
def delete_category(category_id: str, user: CurrentUser = Depends(get_current_user)):
    service.delete_category(category_id)
    return {"success": True}
