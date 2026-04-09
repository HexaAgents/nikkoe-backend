from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import StreamingResponse

from app.errors import AppError, ForbiddenError
from app.middleware.auth import CurrentUser, get_current_user
from app.repositories.receipt import ReceiptRepository
from app.schemas import CreateReceiptRequest, ParseInvoiceResponse, VoidRequest
from app.services import invoice_parser
from app.services.receipt import ReceiptService

repo = ReceiptRepository()
service = ReceiptService(repo)
router = APIRouter(prefix="/api/receipts", tags=["receipts"])


@router.get("/")
def list_receipts(
    limit: int = Query(default=50, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, min_length=1, max_length=100),
    status: str | None = Query(default=None, max_length=20),
    user: CurrentUser = Depends(get_current_user),
):
    return service.list_receipts(limit, offset, search, status)


@router.get("/{receipt_id}")
def get_receipt(receipt_id: int, user: CurrentUser = Depends(get_current_user)):
    return service.get_receipt(receipt_id)


@router.get("/{receipt_id}/lines")
def get_receipt_lines(receipt_id: int, user: CurrentUser = Depends(get_current_user)):
    return service.get_receipt_lines(receipt_id)


@router.post("/", status_code=201)
def create_receipt(body: CreateReceiptRequest, user: CurrentUser = Depends(get_current_user)):
    receipt_data = body.receipt.model_dump()
    if user.profile:
        receipt_data["user_id"] = user.profile.user_id
    return service.create_receipt(
        receipt_data,
        [line.model_dump() for line in body.lines],
    )


@router.post("/parse-invoice", response_model=ParseInvoiceResponse)
async def parse_invoice(
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
):
    if file.content_type not in ("application/pdf", "application/x-pdf"):
        raise AppError(400, "Only PDF files are accepted")
    contents = await file.read()
    return invoice_parser.parse_invoice(contents)


@router.post("/parse-invoice/stream")
async def parse_invoice_stream(
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
):
    if file.content_type not in ("application/pdf", "application/x-pdf"):
        raise AppError(400, "Only PDF files are accepted")
    contents = await file.read()
    return StreamingResponse(
        invoice_parser.parse_invoice_stream(contents),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{receipt_id}/void")
def void_receipt(receipt_id: int, body: VoidRequest, user: CurrentUser = Depends(get_current_user)):
    if not user.profile or not user.profile.user_id:
        raise ForbiddenError("User profile is required to void a receipt")
    service.void_receipt(receipt_id, user.profile.user_id, body.reason)
    return {"success": True}
