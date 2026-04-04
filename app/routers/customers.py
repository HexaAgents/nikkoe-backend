from fastapi import APIRouter, Depends, Query

from app.middleware.auth import CurrentUser, get_current_user
from app.repositories.customer import CustomerRepository
from app.schemas import CustomerInput
from app.services.customer import CustomerService

repo = CustomerRepository()
service = CustomerService(repo)
router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.get("/")
def list_customers(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: CurrentUser = Depends(get_current_user),
):
    return service.list_customers(limit, offset)


@router.post("/", status_code=201)
def create_customer(body: CustomerInput, user: CurrentUser = Depends(get_current_user)):
    return service.create_customer(body.model_dump())
