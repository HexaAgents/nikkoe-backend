"""Tests for API routers using the FastAPI TestClient.

These tests exercise the full HTTP layer — request parsing, Pydantic
validation, auth dependency injection, and response serialization —
while mocking the service layer so no real database calls are made.
"""


# ---------------------------------------------------------------------------
# Auth validation — endpoints reject malformed request bodies
# ---------------------------------------------------------------------------


class TestAuthValidation:
    def test_login_rejects_missing_email(self, client):
        resp = client.post("/api/auth/login", json={"password": "secret"})
        assert resp.status_code == 422

    def test_login_rejects_invalid_email(self, client):
        resp = client.post("/api/auth/login", json={"email": "bad", "password": "secret"})
        assert resp.status_code == 422

    def test_signup_rejects_short_password(self, client):
        resp = client.post("/api/auth/signup", json={"email": "a@b.com", "password": "12345"})
        assert resp.status_code == 422

    def test_signup_rejects_missing_fields(self, client):
        resp = client.post("/api/auth/signup", json={})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Item endpoint validation
# ---------------------------------------------------------------------------


class TestItemValidation:
    def test_create_item_rejects_empty_part_number(self, authed_client):
        resp = authed_client.post("/api/items/", json={"part_number": ""})
        assert resp.status_code == 422

    def test_create_item_rejects_missing_part_number(self, authed_client):
        resp = authed_client.post("/api/items/", json={})
        assert resp.status_code == 422

    def test_create_item_rejects_part_number_too_long(self, authed_client):
        resp = authed_client.post("/api/items/", json={"part_number": "x" * 256})
        assert resp.status_code == 422

    def test_create_item_rejects_description_too_long(self, authed_client):
        resp = authed_client.post(
            "/api/items/",
            json={"part_number": "OK", "description": "x" * 1001},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Category endpoint validation
# ---------------------------------------------------------------------------


class TestCategoryValidation:
    def test_create_category_rejects_empty_name(self, authed_client):
        resp = authed_client.post("/api/categories/", json={"name": ""})
        assert resp.status_code == 422

    def test_create_category_rejects_missing_name(self, authed_client):
        resp = authed_client.post("/api/categories/", json={})
        assert resp.status_code == 422

    def test_create_category_rejects_name_too_long(self, authed_client):
        resp = authed_client.post("/api/categories/", json={"name": "x" * 256})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Location endpoint validation
# ---------------------------------------------------------------------------


class TestLocationValidation:
    def test_create_rejects_empty_code(self, authed_client):
        resp = authed_client.post("/api/locations/", json={"location_code": ""})
        assert resp.status_code == 422

    def test_create_rejects_code_too_long(self, authed_client):
        resp = authed_client.post("/api/locations/", json={"location_code": "x" * 51})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Supplier endpoint validation
# ---------------------------------------------------------------------------


class TestSupplierValidation:
    def test_create_rejects_empty_name(self, authed_client):
        resp = authed_client.post("/api/suppliers/", json={"supplier_name": ""})
        assert resp.status_code == 422

    def test_create_rejects_invalid_email(self, authed_client):
        resp = authed_client.post(
            "/api/suppliers/",
            json={"supplier_name": "Acme", "supplier_email": "bad-email"},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Sale endpoint validation
# ---------------------------------------------------------------------------


class TestSaleValidation:
    def test_create_sale_rejects_invalid_line(self, authed_client):
        resp = authed_client.post(
            "/api/sales/",
            json={
                "sale": {},
                "lines": [
                    {
                        "item_id": "i1",
                        "location_id": "l1",
                        "quantity": 0,
                        "unit_price": 10,
                        "currency_code": "USD",
                    }
                ],
            },
        )
        assert resp.status_code == 422

    def test_create_sale_rejects_negative_price(self, authed_client):
        resp = authed_client.post(
            "/api/sales/",
            json={
                "sale": {},
                "lines": [
                    {
                        "item_id": "i1",
                        "location_id": "l1",
                        "quantity": 1,
                        "unit_price": -5,
                        "currency_code": "USD",
                    }
                ],
            },
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Receipt endpoint validation
# ---------------------------------------------------------------------------


class TestReceiptValidation:
    def test_create_receipt_rejects_invalid_line(self, authed_client):
        resp = authed_client.post(
            "/api/receipts/",
            json={
                "receipt": {},
                "lines": [
                    {
                        "item_id": "i1",
                        "location_id": "l1",
                        "quantity": -1,
                        "unit_cost": 10,
                        "currency_code": "USD",
                    }
                ],
            },
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Void endpoints require a user profile
# ---------------------------------------------------------------------------


class TestVoidRequiresProfile:
    def test_void_sale_forbidden_without_profile(self, unauthed_client):
        resp = unauthed_client.post("/api/sales/1/void", json={})
        assert resp.status_code == 403

    def test_void_receipt_forbidden_without_profile(self, unauthed_client):
        resp = unauthed_client.post("/api/receipts/1/void", json={})
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Supplier quote validation
# ---------------------------------------------------------------------------


class TestSupplierQuoteValidation:
    def test_create_quote_rejects_negative_cost(self, authed_client):
        resp = authed_client.post(
            "/api/supplier-quotes/",
            json={
                "item_id": "i1",
                "supplier_id": "s1",
                "unit_cost": -1,
                "currency": "USD",
            },
        )
        assert resp.status_code == 422

    def test_create_quote_rejects_empty_currency(self, authed_client):
        resp = authed_client.post(
            "/api/supplier-quotes/",
            json={
                "item_id": "i1",
                "supplier_id": "s1",
                "unit_cost": 10,
                "currency": "",
            },
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Customer endpoint validation
# ---------------------------------------------------------------------------


class TestCustomerValidation:
    def test_create_rejects_empty_name(self, authed_client):
        resp = authed_client.post("/api/customers/", json={"name": ""})
        assert resp.status_code == 422

    def test_create_rejects_missing_name(self, authed_client):
        resp = authed_client.post("/api/customers/", json={})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# User endpoint validation
# ---------------------------------------------------------------------------


class TestUserValidation:
    def test_create_user_rejects_invalid_email(self, authed_client):
        resp = authed_client.post(
            "/api/users/",
            json={"email": "not-an-email", "password": "secret123"},
        )
        assert resp.status_code == 422

    def test_create_user_rejects_short_password(self, authed_client):
        resp = authed_client.post(
            "/api/users/",
            json={"email": "a@b.com", "password": "12345"},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Pagination query param validation
# ---------------------------------------------------------------------------


class TestPaginationQueryParams:
    def test_items_rejects_limit_zero(self, authed_client):
        resp = authed_client.get("/api/items/?limit=0")
        assert resp.status_code == 422

    def test_items_rejects_limit_over_max(self, authed_client):
        resp = authed_client.get("/api/items/?limit=100001")
        assert resp.status_code == 422

    def test_items_rejects_negative_offset(self, authed_client):
        resp = authed_client.get("/api/items/?offset=-1")
        assert resp.status_code == 422

    def test_sales_rejects_limit_zero(self, authed_client):
        resp = authed_client.get("/api/sales/?limit=0")
        assert resp.status_code == 422

    def test_receipts_rejects_negative_offset(self, authed_client):
        resp = authed_client.get("/api/receipts/?offset=-1")
        assert resp.status_code == 422

    def test_sales_rejects_limit_over_max(self, authed_client):
        resp = authed_client.get("/api/sales/?limit=5001")
        assert resp.status_code == 422

    def test_receipts_rejects_limit_zero(self, authed_client):
        resp = authed_client.get("/api/receipts/?limit=0")
        assert resp.status_code == 422

    def test_customers_rejects_limit_zero(self, authed_client):
        resp = authed_client.get("/api/customers/?limit=0")
        assert resp.status_code == 422

    def test_channels_rejects_negative_offset(self, authed_client):
        resp = authed_client.get("/api/channels/?offset=-1")
        assert resp.status_code == 422

    def test_currencies_rejects_limit_zero(self, authed_client):
        resp = authed_client.get("/api/currencies/?limit=0")
        assert resp.status_code == 422

    def test_inventory_movements_rejects_negative_offset(self, authed_client):
        resp = authed_client.get("/api/inventory/movements?offset=-1")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Receipt — additional validation edge cases
# ---------------------------------------------------------------------------


class TestReceiptValidationExtra:
    def test_create_receipt_rejects_zero_quantity(self, authed_client):
        resp = authed_client.post(
            "/api/receipts/",
            json={
                "receipt": {},
                "lines": [{"quantity": 0, "unit_price": 10, "currency_id": 1}],
            },
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Sale — additional validation edge cases
# ---------------------------------------------------------------------------


class TestSaleValidationExtra:
    def test_create_sale_rejects_zero_price_negative(self, authed_client):
        resp = authed_client.post(
            "/api/sales/",
            json={
                "sale": {},
                "lines": [{"quantity": 1, "unit_price": -0.01, "currency_id": 1}],
            },
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Inventory transfer validation
# ---------------------------------------------------------------------------


class TestInventoryTransferValidation:
    def test_transfer_rejects_missing_from_stock_id(self, authed_client):
        resp = authed_client.post(
            "/api/inventory/transfer",
            json={"to_location_id": 1, "quantity": 5},
        )
        assert resp.status_code == 422

    def test_transfer_rejects_zero_quantity(self, authed_client):
        resp = authed_client.post(
            "/api/inventory/transfer",
            json={"from_stock_id": 1, "to_location_id": 2, "quantity": 0},
        )
        assert resp.status_code == 422

    def test_transfer_rejects_negative_quantity(self, authed_client):
        resp = authed_client.post(
            "/api/inventory/transfer",
            json={"from_stock_id": 1, "to_location_id": 2, "quantity": -1},
        )
        assert resp.status_code == 422

    def test_transfer_rejects_notes_too_long(self, authed_client):
        resp = authed_client.post(
            "/api/inventory/transfer",
            json={
                "from_stock_id": 1,
                "to_location_id": 2,
                "quantity": 1,
                "notes": "x" * 501,
            },
        )
        assert resp.status_code == 422


class TestCrossTransferValidation:
    def test_cross_transfer_rejects_missing_from_item_id(self, authed_client):
        resp = authed_client.post(
            "/api/inventory/transfer-cross",
            json={"from_location_id": 2, "to_item_id": 3, "to_location_id": 4, "quantity": 5},
        )
        assert resp.status_code == 422

    def test_cross_transfer_rejects_missing_to_item_id(self, authed_client):
        resp = authed_client.post(
            "/api/inventory/transfer-cross",
            json={"from_item_id": 1, "from_location_id": 2, "to_location_id": 4, "quantity": 5},
        )
        assert resp.status_code == 422

    def test_cross_transfer_rejects_zero_quantity(self, authed_client):
        resp = authed_client.post(
            "/api/inventory/transfer-cross",
            json={"from_item_id": 1, "from_location_id": 2, "to_item_id": 3, "to_location_id": 4, "quantity": 0},
        )
        assert resp.status_code == 422

    def test_cross_transfer_rejects_negative_quantity(self, authed_client):
        resp = authed_client.post(
            "/api/inventory/transfer-cross",
            json={"from_item_id": 1, "from_location_id": 2, "to_item_id": 3, "to_location_id": 4, "quantity": -1},
        )
        assert resp.status_code == 422

    def test_cross_transfer_rejects_notes_too_long(self, authed_client):
        payload = {
            "from_item_id": 1,
            "from_location_id": 2,
            "to_item_id": 3,
            "to_location_id": 4,
            "quantity": 1,
            "notes": "x" * 501,
        }
        resp = authed_client.post("/api/inventory/transfer-cross", json=payload)
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Item search validation
# ---------------------------------------------------------------------------


class TestItemSearchValidation:
    def test_search_rejects_missing_query(self, authed_client):
        resp = authed_client.get("/api/items/search")
        assert resp.status_code == 422

    def test_search_rejects_query_too_long(self, authed_client):
        resp = authed_client.get(f"/api/items/search?q={'x' * 256}")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Change password validation
# ---------------------------------------------------------------------------


class TestChangePasswordValidation:
    def test_change_password_rejects_short_new_password(self, authed_client):
        resp = authed_client.post(
            "/api/auth/change-password",
            json={"current_password": "anything", "new_password": "12345"},
        )
        assert resp.status_code == 422

    def test_change_password_rejects_missing_current(self, authed_client):
        resp = authed_client.post(
            "/api/auth/change-password",
            json={"new_password": "new123"},
        )
        assert resp.status_code == 422
