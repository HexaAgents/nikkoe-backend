from fastapi import APIRouter, Depends, Query

from app.errors import ForbiddenError
from app.middleware.auth import CurrentUser, get_current_user
from app.repositories.sale import SaleRepository
from app.schemas import CreateSaleRequest, VoidRequest
from app.services.sale import SaleService

repo = SaleRepository()
service = SaleService(repo)
router = APIRouter(prefix="/api/sales", tags=["sales"])


@router.get("/")
def list_sales(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: CurrentUser = Depends(get_current_user),
):
    return service.list_sales(limit, offset)


@router.get("/{sale_id}")
def get_sale(sale_id: str, user: CurrentUser = Depends(get_current_user)):
    return service.get_sale(sale_id)


@router.get("/{sale_id}/lines")
def get_sale_lines(sale_id: str, user: CurrentUser = Depends(get_current_user)):
    return service.get_sale_lines(sale_id)


@router.post("/", status_code=201)
def create_sale(body: CreateSaleRequest, user: CurrentUser = Depends(get_current_user)):
    return service.create_sale(
        body.sale.model_dump(),
        [line.model_dump() for line in body.lines],
    )


@router.post("/{sale_id}/void")
def void_sale(sale_id: str, body: VoidRequest, user: CurrentUser = Depends(get_current_user)):
    if not user.profile or not user.profile.user_id:
        raise ForbiddenError("User profile is required to void a sale")
    service.void_sale(sale_id, user.profile.user_id, body.reason)
    return {"success": True}
