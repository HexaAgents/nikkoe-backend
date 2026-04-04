from fastapi import APIRouter, Depends, Query

from app.middleware.auth import CurrentUser, get_current_user
from app.repositories.supplier import SupplierRepository
from app.schemas import SupplierInput
from app.services.supplier import SupplierService

repo = SupplierRepository()
service = SupplierService(repo)
router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])


@router.get("/")
def list_suppliers(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: CurrentUser = Depends(get_current_user),
):
    return service.list_suppliers(limit, offset)


@router.post("/", status_code=201)
def create_supplier(body: SupplierInput, user: CurrentUser = Depends(get_current_user)):
    return service.create_supplier(body.model_dump())


@router.delete("/{supplier_id}")
def delete_supplier(supplier_id: str, user: CurrentUser = Depends(get_current_user)):
    service.delete_supplier(supplier_id)
    return {"success": True}
