from fastapi import APIRouter, Depends, Query

from app.errors import ForbiddenError
from app.middleware.auth import CurrentUser, get_current_user
from app.repositories.receipt import ReceiptRepository
from app.schemas import CreateReceiptRequest, VoidRequest
from app.services.receipt import ReceiptService

repo = ReceiptRepository()
service = ReceiptService(repo)
router = APIRouter(prefix="/api/receipts", tags=["receipts"])


@router.get("/")
def list_receipts(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: CurrentUser = Depends(get_current_user),
):
    return service.list_receipts(limit, offset)


@router.get("/{receipt_id}")
def get_receipt(receipt_id: str, user: CurrentUser = Depends(get_current_user)):
    return service.get_receipt(receipt_id)


@router.get("/{receipt_id}/lines")
def get_receipt_lines(receipt_id: str, user: CurrentUser = Depends(get_current_user)):
    return service.get_receipt_lines(receipt_id)


@router.post("/", status_code=201)
def create_receipt(body: CreateReceiptRequest, user: CurrentUser = Depends(get_current_user)):
    return service.create_receipt(
        body.receipt.model_dump(),
        [line.model_dump() for line in body.lines],
    )


@router.post("/{receipt_id}/void")
def void_receipt(receipt_id: str, body: VoidRequest, user: CurrentUser = Depends(get_current_user)):
    if not user.profile or not user.profile.user_id:
        raise ForbiddenError("User profile is required to void a receipt")
    service.void_receipt(receipt_id, user.profile.user_id, body.reason)
    return {"success": True}
