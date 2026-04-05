from fastapi import APIRouter, Depends, Query

from app.middleware.auth import CurrentUser, get_current_user
from app.repositories.currency import CurrencyRepository
from app.services.currency import CurrencyService

repo = CurrencyRepository()
service = CurrencyService(repo)
router = APIRouter(prefix="/api/currencies", tags=["currencies"])


@router.get("/")
def list_currencies(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: CurrentUser = Depends(get_current_user),
):
    return service.list_currencies(limit, offset)
