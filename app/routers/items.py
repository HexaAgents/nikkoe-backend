from fastapi import APIRouter, Depends, Query

from app.middleware.auth import CurrentUser, get_current_user
from app.repositories.inventory import InventoryRepository
from app.repositories.item import ItemRepository
from app.repositories.receipt import ReceiptRepository
from app.repositories.sale import SaleRepository
from app.repositories.supplier_quote import SupplierQuoteRepository
from app.schemas import ItemInput, ItemUpdateInput
from app.services.item import ItemService

item_repo = ItemRepository()
quote_repo = SupplierQuoteRepository()
inventory_repo = InventoryRepository()
receipt_repo = ReceiptRepository()
sale_repo = SaleRepository()
service = ItemService(item_repo, quote_repo, inventory_repo, receipt_repo, sale_repo)
router = APIRouter(prefix="/api/items", tags=["items"])


@router.get("/")
def list_items(
    limit: int = Query(default=20, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    user: CurrentUser = Depends(get_current_user),
):
    return service.list_items(limit, offset)


@router.get("/search")
def search_items(
    q: str = Query(min_length=1, max_length=255),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    in_stock: bool = Query(default=False),
    user: CurrentUser = Depends(get_current_user),
):
    return service.search_items(q, limit, offset, in_stock=in_stock)


@router.get("/{item_id}")
def get_item(item_id: int, user: CurrentUser = Depends(get_current_user)):
    return service.get_item(item_id)


@router.get("/{item_id}/quotes")
def get_item_quotes(item_id: int, user: CurrentUser = Depends(get_current_user)):
    return service.get_item_quotes(item_id)


@router.get("/{item_id}/inventory")
def get_item_inventory(item_id: int, user: CurrentUser = Depends(get_current_user)):
    return service.get_item_inventory(item_id)


@router.get("/{item_id}/receipts")
def get_item_receipts(item_id: int, user: CurrentUser = Depends(get_current_user)):
    return service.get_item_receipts(item_id)


@router.get("/{item_id}/sales")
def get_item_sales(item_id: int, user: CurrentUser = Depends(get_current_user)):
    return service.get_item_sales(item_id)


@router.get("/{item_id}/transfers")
def get_item_transfers(item_id: int, user: CurrentUser = Depends(get_current_user)):
    return service.get_item_transfers(item_id)


@router.post("/", status_code=201)
def create_item(body: ItemInput, user: CurrentUser = Depends(get_current_user)):
    return service.create_item(body.model_dump())


@router.put("/{item_id}")
def update_item(item_id: int, body: ItemUpdateInput, user: CurrentUser = Depends(get_current_user)):
    return service.update_item(item_id, body.model_dump(exclude_none=True))


@router.delete("/{item_id}")
def delete_item(item_id: int, user: CurrentUser = Depends(get_current_user)):
    service.delete_item(item_id)
    return {"success": True}
