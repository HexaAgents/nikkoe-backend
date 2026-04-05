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
    id: int
    name: str


class CustomerInput(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: str | None = None
    phone: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    address_line3: str | None = None
    city: str | None = None
    country: str | None = None
    postal_code: str | None = None


class Customer(BaseModel):
    id: int
    name: str


class Channel(BaseModel):
    id: int
    name: str


class LocationInput(BaseModel):
    code: str = Field(min_length=1, max_length=50)


class Location(BaseModel):
    id: int
    code: str


class ItemInput(BaseModel):
    item_id: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    category_id: int | None = None


class ItemUpdateInput(BaseModel):
    item_id: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    category_id: int | None = None


class Item(BaseModel):
    id: int
    item_id: str
    description: str | None = None
    category_id: int | None = None


class SupplierInput(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    address: str | None = Field(default=None, max_length=500)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=20)


class Supplier(BaseModel):
    id: int
    name: str
    address: str | None = None
    email: str | None = None
    phone: str | None = None


class ReceiptInput(BaseModel):
    supplier_id: int | None = None
    reference: str | None = Field(default=None, max_length=255)
    note: str | None = Field(default=None, max_length=1000)


class ReceiptLineInput(BaseModel):
    stock_id: int | None = None
    item_id: int | None = None
    location_id: int | None = None
    quantity: int = Field(gt=0)
    unit_price: float = Field(ge=0)
    currency_id: int
    supplier_id: int | None = None


class CreateReceiptRequest(BaseModel):
    receipt: ReceiptInput
    lines: list[ReceiptLineInput]


class SaleInput(BaseModel):
    customer_id_id: int | None = None
    channel_id_id: int | None = None
    channel_ref: str | None = None
    note: str | None = Field(default=None, max_length=1000)


class SaleLineInput(BaseModel):
    stock_id: int | None = None
    item_id: int | None = None
    location_id: int | None = None
    quantity: int = Field(gt=0)
    unit_price: float = Field(ge=0)
    currency_id: int


class CreateSaleRequest(BaseModel):
    sale: SaleInput
    lines: list[SaleLineInput]


class SupplierQuoteInput(BaseModel):
    item_id: int
    supplier_id: int
    cost: float = Field(ge=0)
    currency_id: int
    date_time: str | None = None
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
