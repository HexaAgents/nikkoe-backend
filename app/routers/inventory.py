from fastapi import APIRouter, Depends, Query

from app.middleware.auth import CurrentUser, get_current_user
from app.repositories.inventory import InventoryRepository
from app.schemas import CrossTransferInput, TransferInput
from app.services.inventory import InventoryService

repo = InventoryRepository()
service = InventoryService(repo)
router = APIRouter(prefix="/api/inventory", tags=["inventory"])


@router.get("/movements")
def list_movements(
    limit: int = Query(default=50, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, min_length=1, max_length=100),
    user: CurrentUser = Depends(get_current_user),
):
    return service.list_movements(limit, offset, search=search)


@router.get("/stock-valuation")
def stock_valuation(user: CurrentUser = Depends(get_current_user)):
    return service.stock_valuation()


@router.get("/on-hand")
def list_on_hand(user: CurrentUser = Depends(get_current_user)):
    return service.list_on_hand()


@router.post("/transfer", status_code=201)
def transfer_stock(body: TransferInput, user: CurrentUser = Depends(get_current_user)):
    user_id = user.profile.user_id if user.profile else None
    return service.transfer_stock(
        from_stock_id=body.from_stock_id,
        to_location_id=body.to_location_id,
        quantity=body.quantity,
        user_id=user_id,
        notes=body.notes,
    )


@router.post("/transfer-cross", status_code=201)
def cross_transfer_stock(body: CrossTransferInput, user: CurrentUser = Depends(get_current_user)):
    user_id = user.profile.user_id if user.profile else None
    return service.cross_transfer_stock(
        from_item_id=body.from_item_id,
        from_location_id=body.from_location_id,
        to_item_id=body.to_item_id,
        to_location_id=body.to_location_id,
        quantity=body.quantity,
        user_id=user_id,
        notes=body.notes,
    )
