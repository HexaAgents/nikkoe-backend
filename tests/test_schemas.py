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
    CrossTransferInput,
    CustomerInput,
    ItemInput,
    ItemUpdateInput,
    LocationInput,
    LoginInput,
    PaginatedResult,
    PaginationParams,
    ParsedLineItem,
    ParseInvoiceResponse,
    ReceiptInput,
    ReceiptLineInput,
    ResolvedLineItem,
    SaleInput,
    SaleLineInput,
    SignupInput,
    SupplierInput,
    SupplierQuoteInput,
    TransferInput,
    VoidRequest,
)


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


class TestPaginatedResult:
    def test_valid(self):
        r = PaginatedResult(data=[{"a": 1}], total=1)
        assert r.total == 1

    def test_empty(self):
        r = PaginatedResult(data=[], total=0)
        assert r.data == []


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


class TestCustomerInput:
    def test_valid(self):
        assert CustomerInput(name="Acme Corp").name == "Acme Corp"

    def test_rejects_empty(self):
        with pytest.raises(ValidationError):
            CustomerInput(name="")

    def test_rejects_too_long(self):
        with pytest.raises(ValidationError):
            CustomerInput(name="x" * 256)


class TestLocationInput:
    def test_valid(self):
        assert LocationInput(code="WH-A1").code == "WH-A1"

    def test_max_length_50(self):
        loc = LocationInput(code="x" * 50)
        assert len(loc.code) == 50

    def test_rejects_empty(self):
        with pytest.raises(ValidationError):
            LocationInput(code="")

    def test_rejects_over_50(self):
        with pytest.raises(ValidationError):
            LocationInput(code="x" * 51)


class TestItemInput:
    def test_minimal(self):
        item = ItemInput(item_id="ABC-123")
        assert item.item_id == "ABC-123"
        assert item.description is None
        assert item.category_id is None

    def test_fully_populated(self):
        item = ItemInput(item_id="ABC-123", description="A test part", category_id=1)
        assert item.category_id == 1

    def test_rejects_missing_item_id(self):
        with pytest.raises(ValidationError):
            ItemInput()

    def test_rejects_empty_item_id(self):
        with pytest.raises(ValidationError):
            ItemInput(item_id="")

    def test_rejects_item_id_too_long(self):
        with pytest.raises(ValidationError):
            ItemInput(item_id="x" * 256)

    def test_rejects_description_too_long(self):
        with pytest.raises(ValidationError):
            ItemInput(item_id="OK", description="x" * 1001)

    def test_description_at_max(self):
        item = ItemInput(item_id="OK", description="x" * 1000)
        assert len(item.description) == 1000


class TestItemUpdateInput:
    def test_all_none_by_default(self):
        u = ItemUpdateInput()
        assert u.item_id is None
        assert u.description is None
        assert u.category_id is None

    def test_partial_update(self):
        u = ItemUpdateInput(description="Updated")
        assert u.description == "Updated"
        assert u.item_id is None

    def test_rejects_empty_item_id(self):
        with pytest.raises(ValidationError):
            ItemUpdateInput(item_id="")


class TestSupplierInput:
    def test_minimal(self):
        s = SupplierInput(name="Acme")
        assert s.name == "Acme"
        assert s.email is None

    def test_fully_populated(self):
        s = SupplierInput(
            name="Acme Corp",
            address="123 Main St",
            email="contact@acme.com",
            phone="555-0100",
        )
        assert s.email == "contact@acme.com"

    def test_rejects_missing_name(self):
        with pytest.raises(ValidationError):
            SupplierInput()

    def test_rejects_empty_name(self):
        with pytest.raises(ValidationError):
            SupplierInput(name="")

    def test_rejects_name_too_long(self):
        with pytest.raises(ValidationError):
            SupplierInput(name="x" * 256)

    def test_rejects_invalid_email(self):
        with pytest.raises(ValidationError):
            SupplierInput(name="OK", email="not-an-email")

    def test_rejects_phone_too_long(self):
        with pytest.raises(ValidationError):
            SupplierInput(name="OK", phone="1" * 21)

    def test_phone_at_max(self):
        s = SupplierInput(name="OK", phone="1" * 20)
        assert len(s.phone) == 20

    def test_address_at_max(self):
        s = SupplierInput(name="OK", address="x" * 500)
        assert len(s.address) == 500

    def test_rejects_address_too_long(self):
        with pytest.raises(ValidationError):
            SupplierInput(name="OK", address="x" * 501)


class TestReceiptInput:
    def test_all_optional(self):
        r = ReceiptInput()
        assert r.supplier_id is None
        assert r.reference is None
        assert r.note is None

    def test_fully_populated(self):
        r = ReceiptInput(supplier_id=1, reference="PO-123", note="Rush order")
        assert r.reference == "PO-123"

    def test_rejects_reference_too_long(self):
        with pytest.raises(ValidationError):
            ReceiptInput(reference="x" * 256)

    def test_rejects_note_too_long(self):
        with pytest.raises(ValidationError):
            ReceiptInput(note="x" * 1001)


class TestReceiptLineInput:
    VALID = {
        "quantity": 10,
        "unit_price": 5.50,
        "currency_id": 1,
    }

    def test_valid(self):
        line = ReceiptLineInput(**self.VALID)
        assert line.quantity == 10
        assert line.unit_price == 5.50

    def test_rejects_zero_quantity(self):
        with pytest.raises(ValidationError):
            ReceiptLineInput(**{**self.VALID, "quantity": 0})

    def test_rejects_negative_quantity(self):
        with pytest.raises(ValidationError):
            ReceiptLineInput(**{**self.VALID, "quantity": -1})

    def test_allows_zero_unit_price(self):
        line = ReceiptLineInput(**{**self.VALID, "unit_price": 0})
        assert line.unit_price == 0

    def test_rejects_negative_unit_price(self):
        with pytest.raises(ValidationError):
            ReceiptLineInput(**{**self.VALID, "unit_price": -1})


class TestCreateReceiptRequest:
    def test_valid(self):
        req = CreateReceiptRequest(
            receipt=ReceiptInput(),
            lines=[ReceiptLineInput(quantity=1, unit_price=10, currency_id=1)],
        )
        assert len(req.lines) == 1

    def test_empty_lines(self):
        req = CreateReceiptRequest(receipt=ReceiptInput(), lines=[])
        assert req.lines == []

    def test_invalid_line_rejects_whole_request(self):
        with pytest.raises(ValidationError):
            CreateReceiptRequest(
                receipt=ReceiptInput(),
                lines=[ReceiptLineInput(quantity=-1, unit_price=10, currency_id=1)],
            )


class TestSaleInput:
    def test_all_optional(self):
        s = SaleInput()
        assert s.customer_id_id is None
        assert s.channel_id_id is None
        assert s.note is None

    def test_fully_populated(self):
        s = SaleInput(customer_id_id=1, channel_id_id=2, note="Urgent")
        assert s.customer_id_id == 1

    def test_rejects_note_too_long(self):
        with pytest.raises(ValidationError):
            SaleInput(note="x" * 1001)


class TestSaleLineInput:
    VALID = {
        "quantity": 5,
        "unit_price": 10.0,
        "currency_id": 1,
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


class TestCreateSaleRequest:
    def test_valid_with_lines(self):
        req = CreateSaleRequest(
            sale=SaleInput(),
            lines=[SaleLineInput(quantity=2, unit_price=25.0, currency_id=1)],
        )
        assert req.lines[0].currency_id == 1


class TestSupplierQuoteInput:
    VALID = {
        "item_id": 1,
        "supplier_id": 2,
        "cost": 12.50,
        "currency_id": 1,
    }

    def test_valid(self):
        q = SupplierQuoteInput(**self.VALID)
        assert q.cost == 12.50

    def test_with_optional_fields(self):
        q = SupplierQuoteInput(**self.VALID, date_time="2025-01-01", note="Bulk")
        assert q.note == "Bulk"

    def test_allows_zero_cost(self):
        q = SupplierQuoteInput(**{**self.VALID, "cost": 0})
        assert q.cost == 0

    def test_rejects_negative_cost(self):
        with pytest.raises(ValidationError):
            SupplierQuoteInput(**{**self.VALID, "cost": -1})

    def test_rejects_note_too_long(self):
        with pytest.raises(ValidationError):
            SupplierQuoteInput(**{**self.VALID, "note": "x" * 501})

    def test_rejects_missing_item_id(self):
        with pytest.raises(ValidationError):
            SupplierQuoteInput(supplier_id=1, cost=1, currency_id=1)

    def test_rejects_missing_supplier_id(self):
        with pytest.raises(ValidationError):
            SupplierQuoteInput(item_id=1, cost=1, currency_id=1)


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
        login = LoginInput(email="user@example.com", password="any")
        assert login.password == "any"

    def test_rejects_invalid_email(self):
        with pytest.raises(ValidationError):
            LoginInput(email="bad", password="any")

    def test_accepts_any_length_password(self):
        login = LoginInput(email="user@example.com", password="x")
        assert login.password == "x"


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


class TestTransferInput:
    def test_valid(self):
        t = TransferInput(from_stock_id=1, to_location_id=2, quantity=5)
        assert t.quantity == 5

    def test_rejects_zero_quantity(self):
        with pytest.raises(ValidationError):
            TransferInput(from_stock_id=1, to_location_id=2, quantity=0)

    def test_rejects_negative_quantity(self):
        with pytest.raises(ValidationError):
            TransferInput(from_stock_id=1, to_location_id=2, quantity=-1)

    def test_notes_optional(self):
        t = TransferInput(from_stock_id=1, to_location_id=2, quantity=1)
        assert t.notes is None

    def test_notes_at_max(self):
        t = TransferInput(from_stock_id=1, to_location_id=2, quantity=1, notes="x" * 500)
        assert len(t.notes) == 500

    def test_rejects_notes_too_long(self):
        with pytest.raises(ValidationError):
            TransferInput(from_stock_id=1, to_location_id=2, quantity=1, notes="x" * 501)


class TestCrossTransferInput:
    def test_valid(self):
        t = CrossTransferInput(from_item_id=1, from_location_id=2, to_item_id=3, to_location_id=4, quantity=10)
        assert t.quantity == 10

    def test_rejects_missing_from_item_id(self):
        with pytest.raises(ValidationError):
            CrossTransferInput(from_location_id=2, to_item_id=3, to_location_id=4, quantity=10)

    def test_rejects_missing_to_item_id(self):
        with pytest.raises(ValidationError):
            CrossTransferInput(from_item_id=1, from_location_id=2, to_location_id=4, quantity=10)

    def test_rejects_zero_quantity(self):
        with pytest.raises(ValidationError):
            CrossTransferInput(from_item_id=1, from_location_id=2, to_item_id=3, to_location_id=4, quantity=0)

    def test_rejects_negative_quantity(self):
        with pytest.raises(ValidationError):
            CrossTransferInput(from_item_id=1, from_location_id=2, to_item_id=3, to_location_id=4, quantity=-1)

    def test_notes_optional(self):
        t = CrossTransferInput(from_item_id=1, from_location_id=2, to_item_id=3, to_location_id=4, quantity=1)
        assert t.notes is None

    def test_rejects_notes_too_long(self):
        with pytest.raises(ValidationError):
            CrossTransferInput(
                from_item_id=1,
                from_location_id=2,
                to_item_id=3,
                to_location_id=4,
                quantity=1,
                notes="x" * 501,
            )


class TestParsedLineItem:
    def test_valid(self):
        item = ParsedLineItem(part_number="ABC-123", quantity=5, unit_price=10.50)
        assert item.part_number == "ABC-123"
        assert item.description is None

    def test_with_description(self):
        item = ParsedLineItem(part_number="X", description="Widget", quantity=1, unit_price=0.0)
        assert item.description == "Widget"

    def test_rejects_missing_part_number(self):
        with pytest.raises(ValidationError):
            ParsedLineItem(quantity=1, unit_price=1.0)

    def test_rejects_missing_quantity(self):
        with pytest.raises(ValidationError):
            ParsedLineItem(part_number="X", unit_price=1.0)

    def test_rejects_missing_unit_price(self):
        with pytest.raises(ValidationError):
            ParsedLineItem(part_number="X", quantity=1)


class TestResolvedLineItem:
    def test_valid_with_matches(self):
        item = ResolvedLineItem(
            part_number="ABC",
            quantity=1,
            unit_price=5.0,
            matched_item_id=10,
            matched_item_name="ABC",
            matched_location_id=20,
            matched_location_code="WH-A",
        )
        assert item.matched_item_id == 10

    def test_matches_default_to_none(self):
        item = ResolvedLineItem(part_number="X", quantity=1, unit_price=1.0)
        assert item.matched_item_id is None
        assert item.matched_location_id is None

    def test_inherits_parsed_fields(self):
        item = ResolvedLineItem(part_number="Y", quantity=3, unit_price=2.0, description="Desc")
        assert item.description == "Desc"
        assert item.quantity == 3


class TestParseInvoiceResponse:
    def test_valid_with_lines(self):
        resp = ParseInvoiceResponse(lines=[ResolvedLineItem(part_number="X", quantity=1, unit_price=5.0)])
        assert len(resp.lines) == 1
        assert resp.supplier_name is None

    def test_all_optional_fields(self):
        resp = ParseInvoiceResponse(
            supplier_name="Acme",
            matched_supplier_id=1,
            reference="INV-001",
            currency_symbol="£",
            note="Test",
            lines=[],
        )
        assert resp.supplier_name == "Acme"
        assert resp.reference == "INV-001"

    def test_rejects_missing_lines(self):
        with pytest.raises(ValidationError):
            ParseInvoiceResponse(supplier_name="X")

    def test_empty_lines_is_valid(self):
        resp = ParseInvoiceResponse(lines=[])
        assert resp.lines == []


class TestVoidRequest:
    def test_empty(self):
        v = VoidRequest()
        assert v.reason is None

    def test_with_reason(self):
        v = VoidRequest(reason="Duplicate entry")
        assert v.reason == "Duplicate entry"
