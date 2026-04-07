from fastapi import APIRouter, Depends, Query

from app.middleware.auth import CurrentUser, get_current_user
from app.repositories.category import CategoryRepository
from app.repositories.item import ItemRepository
from app.schemas import CategoryInput
from app.services.category import CategoryService

repo = CategoryRepository()
item_repo = ItemRepository()
service = CategoryService(repo, item_repo)
router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("/")
def list_categories(
    limit: int = Query(default=5000, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    user: CurrentUser = Depends(get_current_user),
):
    return service.list_categories(limit, offset)


@router.get("/{category_id}")
def get_category(category_id: int, user: CurrentUser = Depends(get_current_user)):
    return service.get_category(category_id)


@router.get("/{category_id}/items")
def get_category_items(
    category_id: int,
    limit: int = Query(default=5000, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    user: CurrentUser = Depends(get_current_user),
):
    return service.get_category_items(category_id, limit, offset)


@router.post("/", status_code=201)
def create_category(body: CategoryInput, user: CurrentUser = Depends(get_current_user)):
    return service.create_category(body.model_dump())


@router.delete("/{category_id}")
def delete_category(category_id: int, user: CurrentUser = Depends(get_current_user)):
    service.delete_category(category_id)
    return {"success": True}
