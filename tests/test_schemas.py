"""Tests for all Pydantic schemas in app/schemas.py.

Every schema is tested for:
- Happy path: valid input is accepted
- Boundary values: min/max lengths, edge-case numbers
- Rejection: invalid input raises ValidationError
"""

import pytest
from pydantic import ValidationError

from app.schemas import (
    CategoryInput,
    ChangePasswordInput,
    CreateReceiptRequest,
    CreateSaleRequest,
    CreateUserInput,
    CustomerInput,
    ItemInput,
    ItemUpdateInput,
    LocationInput,
    LoginInput,
    PaginatedResult,
    PaginationParams,
    ReceiptInput,
    ReceiptLineInput,
    SaleInput,
    SaleLineInput,
    SignupInput,
    SupplierInput,
    SupplierQuoteInput,
    VoidRequest,
)


# ---------------------------------------------------------------------------
# PaginationParams
# ---------------------------------------------------------------------------

class TestPaginationParams:
    def test_defaults(self):
        p = PaginationParams()
        assert p.limit == 50
        assert p.offset == 0

    def test_custom_values(self):
        p = PaginationParams(limit=10, offset=20)
        assert p.limit == 10
        assert p.offset == 20

    def test_limit_minimum(self):
        p = PaginationParams(limit=1)
        assert p.limit == 1

    def test_limit_maximum(self):
        p = PaginationParams(limit=100)
        assert p.limit == 100

    @pytest.mark.parametrize("val", [0, -1, 101, 999])
    def test_limit_out_of_range(self, val):
        with pytest.raises(ValidationError):
            PaginationParams(limit=val)

    def test_negative_offset_rejected(self):
        with pytest.raises(ValidationError):
            PaginationParams(offset=-1)


# ---------------------------------------------------------------------------
# PaginatedResult
# ---------------------------------------------------------------------------

class TestPaginatedResult:
    def test_valid(self):
        r = PaginatedResult(data=[{"a": 1}], total=1)
        assert r.total == 1
        assert len(r.data) == 1

    def test_empty(self):
        r = PaginatedResult(data=[], total=0)
        assert r.data == []


# ---------------------------------------------------------------------------
# CategoryInput
# ---------------------------------------------------------------------------

class TestCategoryInput:
    def test_valid(self):
        c = CategoryInput(name="Electronics")
        assert c.name == "Electronics"

    def test_max_length(self):
        c = CategoryInput(name="x" * 255)
        assert len(c.name) == 255

    def test_rejects_empty(self):
        with pytest.raises(ValidationError):
            CategoryInput(name="")

    def test_rejects_too_long(self):
        with pytest.raises(ValidationError):
            CategoryInput(name="x" * 256)


# ---------------------------------------------------------------------------
# CustomerInput
# ---------------------------------------------------------------------------

class TestCustomerInput:
    def test_valid(self):
        assert CustomerInput(name="Acme Corp").name == "Acme Corp"

    def test_rejects_empty(self):
        with pytest.raises(ValidationError):
            CustomerInput(name="")

    def test_rejects_too_long(self):
        with pytest.raises(ValidationError):
            CustomerInput(name="x" * 256)


# ---------------------------------------------------------------------------
# LocationInput
# ---------------------------------------------------------------------------

class TestLocationInput:
    def test_valid(self):
        assert LocationInput(location_code="WH-A1").location_code == "WH-A1"

    def test_max_length_50(self):
        loc = LocationInput(location_code="x" * 50)
        assert len(loc.location_code) == 50

    def test_rejects_empty(self):
        with pytest.raises(ValidationError):
            LocationInput(location_code="")

    def test_rejects_over_50(self):
        with pytest.raises(ValidationError):
            LocationInput(location_code="x" * 51)


# ---------------------------------------------------------------------------
# ItemInput
# ---------------------------------------------------------------------------

class TestItemInput:
    def test_minimal(self):
        item = ItemInput(part_number="ABC-123")
        assert item.part_number == "ABC-123"
        assert item.description is None
        assert item.category_id is None

    def test_fully_populated(self):
        item = ItemInput(
            part_number="ABC-123",
            description="A test part",
            category_id="cat-uuid",
        )
        assert item.category_id == "cat-uuid"

    def test_rejects_missing_part_number(self):
        with pytest.raises(ValidationError):
            ItemInput()

    def test_rejects_empty_part_number(self):
        with pytest.raises(ValidationError):
            ItemInput(part_number="")

    def test_rejects_part_number_too_long(self):
        with pytest.raises(ValidationError):
            ItemInput(part_number="x" * 256)

    def test_rejects_description_too_long(self):
        with pytest.raises(ValidationError):
            ItemInput(part_number="OK", description="x" * 1001)

    def test_description_at_max(self):
        item = ItemInput(part_number="OK", description="x" * 1000)
        assert len(item.description) == 1000


# ---------------------------------------------------------------------------
# ItemUpdateInput
# ---------------------------------------------------------------------------

class TestItemUpdateInput:
    def test_all_none_by_default(self):
        u = ItemUpdateInput()
        assert u.part_number is None
        assert u.description is None
        assert u.category_id is None

    def test_partial_update(self):
        u = ItemUpdateInput(description="Updated")
        assert u.description == "Updated"
        assert u.part_number is None

    def test_rejects_empty_part_number(self):
        with pytest.raises(ValidationError):
            ItemUpdateInput(part_number="")


# ---------------------------------------------------------------------------
# SupplierInput
# ---------------------------------------------------------------------------

class TestSupplierInput:
    def test_minimal(self):
        s = SupplierInput(supplier_name="Acme")
        assert s.supplier_name == "Acme"
        assert s.supplier_email is None

    def test_fully_populated(self):
        s = SupplierInput(
            supplier_name="Acme Corp",
            supplier_address="123 Main St",
            supplier_email="contact@acme.com",
            supplier_phone="555-0100",
        )
        assert s.supplier_email == "contact@acme.com"

    def test_rejects_missing_name(self):
        with pytest.raises(ValidationError):
            SupplierInput()

    def test_rejects_empty_name(self):
        with pytest.raises(ValidationError):
            SupplierInput(supplier_name="")

    def test_rejects_name_too_long(self):
        with pytest.raises(ValidationError):
            SupplierInput(supplier_name="x" * 256)

    def test_rejects_invalid_email(self):
        with pytest.raises(ValidationError):
            SupplierInput(supplier_name="OK", supplier_email="not-an-email")

    def test_rejects_phone_too_long(self):
        with pytest.raises(ValidationError):
            SupplierInput(supplier_name="OK", supplier_phone="1" * 21)

    def test_phone_at_max(self):
        s = SupplierInput(supplier_name="OK", supplier_phone="1" * 20)
        assert len(s.supplier_phone) == 20

    def test_address_at_max(self):
        s = SupplierInput(supplier_name="OK", supplier_address="x" * 500)
        assert len(s.supplier_address) == 500

    def test_rejects_address_too_long(self):
        with pytest.raises(ValidationError):
            SupplierInput(supplier_name="OK", supplier_address="x" * 501)


# ---------------------------------------------------------------------------
# ReceiptInput / ReceiptLineInput / CreateReceiptRequest
# ---------------------------------------------------------------------------

class TestReceiptInput:
    def test_all_optional(self):
        r = ReceiptInput()
        assert r.supplier_id is None
        assert r.reference is None
        assert r.note is None

    def test_fully_populated(self):
        r = ReceiptInput(supplier_id="sup-1", reference="PO-123", note="Rush order")
        assert r.reference == "PO-123"

    def test_rejects_reference_too_long(self):
        with pytest.raises(ValidationError):
            ReceiptInput(reference="x" * 256)

    def test_rejects_note_too_long(self):
        with pytest.raises(ValidationError):
            ReceiptInput(note="x" * 1001)


class TestReceiptLineInput:
    VALID = {
        "item_id": "item-1",
        "location_id": "loc-1",
        "quantity": 10,
        "unit_cost": 5.50,
        "currency_code": "USD",
    }

    def test_valid(self):
        line = ReceiptLineInput(**self.VALID)
        assert line.quantity == 10
        assert line.unit_cost == 5.50

    def test_rejects_zero_quantity(self):
        with pytest.raises(ValidationError):
            ReceiptLineInput(**{**self.VALID, "quantity": 0})

    def test_rejects_negative_quantity(self):
        with pytest.raises(ValidationError):
            ReceiptLineInput(**{**self.VALID, "quantity": -1})

    def test_allows_zero_unit_cost(self):
        line = ReceiptLineInput(**{**self.VALID, "unit_cost": 0})
        assert line.unit_cost == 0

    def test_rejects_negative_unit_cost(self):
        with pytest.raises(ValidationError):
            ReceiptLineInput(**{**self.VALID, "unit_cost": -1})

    def test_rejects_empty_currency(self):
        with pytest.raises(ValidationError):
            ReceiptLineInput(**{**self.VALID, "currency_code": ""})

    def test_rejects_currency_too_long(self):
        with pytest.raises(ValidationError):
            ReceiptLineInput(**{**self.VALID, "currency_code": "TOOLONGCURR"})

    def test_rejects_missing_item_id(self):
        data = {k: v for k, v in self.VALID.items() if k != "item_id"}
        with pytest.raises(ValidationError):
            ReceiptLineInput(**data)


class TestCreateReceiptRequest:
    def test_valid(self):
        req = CreateReceiptRequest(
            receipt=ReceiptInput(),
            lines=[
                ReceiptLineInput(
                    item_id="i1", location_id="l1", quantity=1,
                    unit_cost=10, currency_code="USD",
                )
            ],
        )
        assert len(req.lines) == 1

    def test_empty_lines(self):
        req = CreateReceiptRequest(receipt=ReceiptInput(), lines=[])
        assert req.lines == []

    def test_invalid_line_rejects_whole_request(self):
        with pytest.raises(ValidationError):
            CreateReceiptRequest(
                receipt=ReceiptInput(),
                lines=[
                    ReceiptLineInput(
                        item_id="i1", location_id="l1", quantity=-1,
                        unit_cost=10, currency_code="USD",
                    )
                ],
            )


# ---------------------------------------------------------------------------
# SaleInput / SaleLineInput / CreateSaleRequest
# ---------------------------------------------------------------------------

class TestSaleInput:
    def test_all_optional(self):
        s = SaleInput()
        assert s.customer_name is None
        assert s.channel_id is None
        assert s.note is None

    def test_fully_populated(self):
        s = SaleInput(customer_name="Acme", channel_id="ch-1", note="Urgent")
        assert s.customer_name == "Acme"

    def test_rejects_customer_too_long(self):
        with pytest.raises(ValidationError):
            SaleInput(customer_name="x" * 256)

    def test_rejects_note_too_long(self):
        with pytest.raises(ValidationError):
            SaleInput(note="x" * 1001)


class TestSaleLineInput:
    VALID = {
        "item_id": "item-1",
        "location_id": "loc-1",
        "quantity": 5,
        "unit_price": 10.0,
        "currency_code": "USD",
    }

    def test_valid(self):
        line = SaleLineInput(**self.VALID)
        assert line.quantity == 5

    def test_rejects_zero_quantity(self):
        with pytest.raises(ValidationError):
            SaleLineInput(**{**self.VALID, "quantity": 0})

    def test_rejects_negative_unit_price(self):
        with pytest.raises(ValidationError):
            SaleLineInput(**{**self.VALID, "unit_price": -5})

    def test_allows_zero_unit_price(self):
        line = SaleLineInput(**{**self.VALID, "unit_price": 0})
        assert line.unit_price == 0

    def test_rejects_empty_currency(self):
        with pytest.raises(ValidationError):
            SaleLineInput(**{**self.VALID, "currency_code": ""})


class TestCreateSaleRequest:
    def test_valid_with_lines(self):
        req = CreateSaleRequest(
            sale=SaleInput(),
            lines=[
                SaleLineInput(
                    item_id="i1", location_id="l1", quantity=2,
                    unit_price=25.0, currency_code="EUR",
                )
            ],
        )
        assert req.lines[0].currency_code == "EUR"


# ---------------------------------------------------------------------------
# SupplierQuoteInput
# ---------------------------------------------------------------------------

class TestSupplierQuoteInput:
    VALID = {
        "item_id": "item-1",
        "supplier_id": "sup-1",
        "unit_cost": 12.50,
        "currency": "USD",
    }

    def test_valid(self):
        q = SupplierQuoteInput(**self.VALID)
        assert q.unit_cost == 12.50

    def test_with_optional_fields(self):
        q = SupplierQuoteInput(**self.VALID, quoted_at="2025-01-01", note="Bulk")
        assert q.note == "Bulk"

    def test_allows_zero_unit_cost(self):
        q = SupplierQuoteInput(**{**self.VALID, "unit_cost": 0})
        assert q.unit_cost == 0

    def test_rejects_negative_unit_cost(self):
        with pytest.raises(ValidationError):
            SupplierQuoteInput(**{**self.VALID, "unit_cost": -1})

    def test_rejects_empty_currency(self):
        with pytest.raises(ValidationError):
            SupplierQuoteInput(**{**self.VALID, "currency": ""})

    def test_rejects_currency_too_long(self):
        with pytest.raises(ValidationError):
            SupplierQuoteInput(**{**self.VALID, "currency": "TOOLONGCURR"})

    def test_rejects_note_too_long(self):
        with pytest.raises(ValidationError):
            SupplierQuoteInput(**{**self.VALID, "note": "x" * 501})

    def test_rejects_missing_item_id(self):
        with pytest.raises(ValidationError):
            SupplierQuoteInput(supplier_id="s1", unit_cost=1, currency="USD")

    def test_rejects_missing_supplier_id(self):
        with pytest.raises(ValidationError):
            SupplierQuoteInput(item_id="i1", unit_cost=1, currency="USD")


# ---------------------------------------------------------------------------
# Auth schemas
# ---------------------------------------------------------------------------

class TestCreateUserInput:
    def test_valid(self):
        u = CreateUserInput(email="user@example.com", password="secret123")
        assert u.email == "user@example.com"

    def test_rejects_invalid_email(self):
        with pytest.raises(ValidationError):
            CreateUserInput(email="not-email", password="secret123")

    def test_rejects_short_password(self):
        with pytest.raises(ValidationError):
            CreateUserInput(email="user@example.com", password="12345")

    def test_accepts_exactly_6_char_password(self):
        u = CreateUserInput(email="user@example.com", password="123456")
        assert len(u.password) == 6


class TestLoginInput:
    def test_valid(self):
        l = LoginInput(email="user@example.com", password="any")
        assert l.password == "any"

    def test_rejects_invalid_email(self):
        with pytest.raises(ValidationError):
            LoginInput(email="bad", password="any")

    def test_accepts_any_length_password(self):
        l = LoginInput(email="user@example.com", password="x")
        assert l.password == "x"


class TestSignupInput:
    def test_valid(self):
        s = SignupInput(email="user@example.com", password="secret123")
        assert s.email == "user@example.com"

    def test_rejects_short_password(self):
        with pytest.raises(ValidationError):
            SignupInput(email="user@example.com", password="12345")


class TestChangePasswordInput:
    def test_valid(self):
        c = ChangePasswordInput(current_password="old", new_password="newsecret")
        assert c.new_password == "newsecret"

    def test_rejects_short_new_password(self):
        with pytest.raises(ValidationError):
            ChangePasswordInput(current_password="old", new_password="12345")

    def test_current_password_any_length(self):
        c = ChangePasswordInput(current_password="x", new_password="123456")
        assert c.current_password == "x"


# ---------------------------------------------------------------------------
# VoidRequest
# ---------------------------------------------------------------------------

class TestVoidRequest:
    def test_empty(self):
        v = VoidRequest()
        assert v.reason is None

    def test_with_reason(self):
        v = VoidRequest(reason="Duplicate entry")
        assert v.reason == "Duplicate entry"
