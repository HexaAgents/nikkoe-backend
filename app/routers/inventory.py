from fastapi import APIRouter, Depends, Query

from app.middleware.auth import CurrentUser, get_current_user
from app.repositories.inventory import InventoryRepository
from app.services.inventory import InventoryService

repo = InventoryRepository()
service = InventoryService(repo)
router = APIRouter(prefix="/api/inventory", tags=["inventory"])


@router.get("/movements")
def list_movements(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: CurrentUser = Depends(get_current_user),
):
    return service.list_movements(limit, offset)


@router.get("/on-hand")
def list_on_hand(user: CurrentUser = Depends(get_current_user)):
    return service.list_on_hand()
