from fastapi import APIRouter, Depends, HTTPException, Query

from app.middleware.auth import CurrentUser, get_current_user
from app.repositories.supplier import SupplierRepository
from app.repositories.supplier_alias import SupplierAliasRepository
from app.schemas import SupplierAliasInput, SupplierInput
from app.services.supplier import SupplierService

repo = SupplierRepository()
service = SupplierService(repo)
alias_repo = SupplierAliasRepository()
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


@router.get("/{supplier_id}/aliases")
def list_supplier_aliases(supplier_id: int, user: CurrentUser = Depends(get_current_user)):
    return alias_repo.find_by_supplier(supplier_id)


@router.post("/{supplier_id}/aliases", status_code=201)
def create_supplier_alias(
    supplier_id: int,
    body: SupplierAliasInput,
    user: CurrentUser = Depends(get_current_user),
):
    if not service.get_supplier(supplier_id):
        raise HTTPException(status_code=404, detail="Supplier not found")
    created_by = user.profile.user_id if user.profile else None
    return alias_repo.upsert(supplier_id, body.alias, created_by=created_by)


@router.delete("/aliases/{alias_id}")
def delete_supplier_alias(alias_id: int, user: CurrentUser = Depends(get_current_user)):
    alias_repo.remove(alias_id)
    return {"success": True}
