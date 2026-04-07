from fastapi import APIRouter, Depends, HTTPException, Query

from app.middleware.auth import CurrentUser, get_current_user
from app.repositories.supplier import SupplierRepository
from app.schemas import SupplierInput
from app.services.supplier import SupplierService

repo = SupplierRepository()
service = SupplierService(repo)
router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])


@router.get("/")
def list_suppliers(
    limit: int = Query(default=5000, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, min_length=1, max_length=100),
    user: CurrentUser = Depends(get_current_user),
):
    return service.list_suppliers(limit, offset, search=search)


@router.get("/{supplier_id}")
def get_supplier(supplier_id: int, user: CurrentUser = Depends(get_current_user)):
    supplier = service.get_supplier(supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier


@router.get("/{supplier_id}/receipts")
def get_supplier_receipts(supplier_id: int, user: CurrentUser = Depends(get_current_user)):
    return service.get_supplier_receipts(supplier_id)


@router.post("/", status_code=201)
def create_supplier(body: SupplierInput, user: CurrentUser = Depends(get_current_user)):
    return service.create_supplier(body.model_dump())


@router.delete("/{supplier_id}")
def delete_supplier(supplier_id: int, user: CurrentUser = Depends(get_current_user)):
    service.delete_supplier(supplier_id)
    return {"success": True}
