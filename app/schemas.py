from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, EmailStr, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class PaginatedResult(BaseModel, Generic[T]):
    data: list[T]
    total: int


class CategoryInput(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class Category(BaseModel):
    category_id: str
    name: str


class CustomerInput(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class Customer(BaseModel):
    customer_id: str
    name: str


class Channel(BaseModel):
    channel_id: str
    channel_name: str


class LocationInput(BaseModel):
    location_code: str = Field(min_length=1, max_length=50)


class Location(BaseModel):
    location_id: str
    location_code: str


class ItemInput(BaseModel):
    part_number: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    category_id: str | None = None


class ItemUpdateInput(BaseModel):
    part_number: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    category_id: str | None = None


class Item(BaseModel):
    item_id: str
    part_number: str
    description: str | None = None
    category_id: str | None = None


class SupplierInput(BaseModel):
    supplier_name: str = Field(min_length=1, max_length=255)
    supplier_address: str | None = Field(default=None, max_length=500)
    supplier_email: EmailStr | None = None
    supplier_phone: str | None = Field(default=None, max_length=20)


class Supplier(BaseModel):
    supplier_id: str
    supplier_name: str
    supplier_address: str | None = None
    supplier_email: str | None = None
    supplier_phone: str | None = None


class ReceiptInput(BaseModel):
    supplier_id: str | None = None
    reference: str | None = Field(default=None, max_length=255)
    note: str | None = Field(default=None, max_length=1000)


class ReceiptLineInput(BaseModel):
    item_id: str
    location_id: str
    quantity: int = Field(gt=0)
    unit_cost: float = Field(ge=0)
    currency_code: str = Field(min_length=1, max_length=10)


class CreateReceiptRequest(BaseModel):
    receipt: ReceiptInput
    lines: list[ReceiptLineInput]


class SaleInput(BaseModel):
    customer_name: str | None = Field(default=None, max_length=255)
    channel_id: str | None = None
    note: str | None = Field(default=None, max_length=1000)


class SaleLineInput(BaseModel):
    item_id: str
    location_id: str
    quantity: int = Field(gt=0)
    unit_price: float = Field(ge=0)
    currency_code: str = Field(min_length=1, max_length=10)


class CreateSaleRequest(BaseModel):
    sale: SaleInput
    lines: list[SaleLineInput]


class SupplierQuoteInput(BaseModel):
    item_id: str
    supplier_id: str
    unit_cost: float = Field(ge=0)
    currency: str = Field(min_length=1, max_length=10)
    quoted_at: str | None = None
    note: str | None = Field(default=None, max_length=500)


class CreateUserInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class LoginInput(BaseModel):
    email: EmailStr
    password: str


class SignupInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class ChangePasswordInput(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6)


class VoidRequest(BaseModel):
    reason: str | None = None
