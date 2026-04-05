from fastapi import APIRouter, Depends

from app.middleware.auth import CurrentUser, get_current_user
from app.repositories.supplier_quote import SupplierQuoteRepository
from app.schemas import SupplierQuoteInput
from app.services.supplier_quote import SupplierQuoteService

repo = SupplierQuoteRepository()
service = SupplierQuoteService(repo)
router = APIRouter(prefix="/api/supplier-quotes", tags=["supplier-quotes"])


@router.post("/", status_code=201)
def create_quote(body: SupplierQuoteInput, user: CurrentUser = Depends(get_current_user)):
    return service.create_quote(body.model_dump())


@router.delete("/{quote_id}")
def delete_quote(quote_id: int, user: CurrentUser = Depends(get_current_user)):
    service.delete_quote(quote_id)
    return {"success": True}
