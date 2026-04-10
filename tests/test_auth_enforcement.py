"""Auth enforcement tests — every protected endpoint must return 401 without a token.

Uses the raw ``client`` fixture (no auth override).  The real
``get_current_user`` dependency runs, finds no Authorization header,
and raises HTTPException(401) before any body parsing occurs.

If a developer accidentally removes ``Depends(get_current_user)`` from
an endpoint, the corresponding test here will fail.
"""


# ── Sales ────────────────────────────────────────────────────────────


class TestSalesAuthEnforcement:
    def test_list_sales_requires_auth(self, client):
        assert client.get("/api/sales/").status_code == 401

    def test_get_sale_requires_auth(self, client):
        assert client.get("/api/sales/1").status_code == 401

    def test_get_sale_lines_requires_auth(self, client):
        assert client.get("/api/sales/1/lines").status_code == 401

    def test_create_sale_requires_auth(self, client):
        assert client.post("/api/sales/", json={}).status_code == 401

    def test_void_sale_requires_auth(self, client):
        assert client.post("/api/sales/1/void", json={}).status_code == 401


# ── Receipts ─────────────────────────────────────────────────────────


class TestReceiptsAuthEnforcement:
    def test_list_receipts_requires_auth(self, client):
        assert client.get("/api/receipts/").status_code == 401

    def test_get_receipt_requires_auth(self, client):
        assert client.get("/api/receipts/1").status_code == 401

    def test_get_receipt_lines_requires_auth(self, client):
        assert client.get("/api/receipts/1/lines").status_code == 401

    def test_create_receipt_requires_auth(self, client):
        assert client.post("/api/receipts/", json={}).status_code == 401

    def test_void_receipt_requires_auth(self, client):
        assert client.post("/api/receipts/1/void", json={}).status_code == 401


# ── Items ────────────────────────────────────────────────────────────


class TestItemsAuthEnforcement:
    def test_list_items_requires_auth(self, client):
        assert client.get("/api/items/").status_code == 401

    def test_search_items_requires_auth(self, client):
        assert client.get("/api/items/search?q=x").status_code == 401

    def test_get_item_requires_auth(self, client):
        assert client.get("/api/items/1").status_code == 401

    def test_get_item_quotes_requires_auth(self, client):
        assert client.get("/api/items/1/quotes").status_code == 401

    def test_get_item_inventory_requires_auth(self, client):
        assert client.get("/api/items/1/inventory").status_code == 401

    def test_get_item_receipts_requires_auth(self, client):
        assert client.get("/api/items/1/receipts").status_code == 401

    def test_get_item_sales_requires_auth(self, client):
        assert client.get("/api/items/1/sales").status_code == 401

    def test_get_items_by_search_id_requires_auth(self, client):
        assert client.get("/api/items/by-search-id/asd").status_code == 401

    def test_create_item_requires_auth(self, client):
        assert client.post("/api/items/", json={}).status_code == 401

    def test_update_item_requires_auth(self, client):
        assert client.put("/api/items/1", json={}).status_code == 401

    def test_delete_item_requires_auth(self, client):
        assert client.delete("/api/items/1").status_code == 401


# ── Categories ───────────────────────────────────────────────────────


class TestCategoriesAuthEnforcement:
    def test_list_categories_requires_auth(self, client):
        assert client.get("/api/categories/").status_code == 401

    def test_create_category_requires_auth(self, client):
        assert client.post("/api/categories/", json={}).status_code == 401

    def test_delete_category_requires_auth(self, client):
        assert client.delete("/api/categories/1").status_code == 401


# ── Locations ────────────────────────────────────────────────────────


class TestLocationsAuthEnforcement:
    def test_list_locations_requires_auth(self, client):
        assert client.get("/api/locations/").status_code == 401

    def test_create_location_requires_auth(self, client):
        assert client.post("/api/locations/", json={}).status_code == 401

    def test_delete_location_requires_auth(self, client):
        assert client.delete("/api/locations/1").status_code == 401


# ── Suppliers ────────────────────────────────────────────────────────


class TestSuppliersAuthEnforcement:
    def test_list_suppliers_requires_auth(self, client):
        assert client.get("/api/suppliers/").status_code == 401

    def test_create_supplier_requires_auth(self, client):
        assert client.post("/api/suppliers/", json={}).status_code == 401

    def test_delete_supplier_requires_auth(self, client):
        assert client.delete("/api/suppliers/1").status_code == 401


# ── Customers ────────────────────────────────────────────────────────


class TestCustomersAuthEnforcement:
    def test_list_customers_requires_auth(self, client):
        assert client.get("/api/customers/").status_code == 401

    def test_create_customer_requires_auth(self, client):
        assert client.post("/api/customers/", json={}).status_code == 401


# ── Channels ─────────────────────────────────────────────────────────


class TestChannelsAuthEnforcement:
    def test_list_channels_requires_auth(self, client):
        assert client.get("/api/channels/").status_code == 401


# ── Currencies ───────────────────────────────────────────────────────


class TestCurrenciesAuthEnforcement:
    def test_list_currencies_requires_auth(self, client):
        assert client.get("/api/currencies/").status_code == 401


# ── Inventory ────────────────────────────────────────────────────────


class TestInventoryAuthEnforcement:
    def test_list_movements_requires_auth(self, client):
        assert client.get("/api/inventory/movements").status_code == 401

    def test_stock_valuation_requires_auth(self, client):
        assert client.get("/api/inventory/stock-valuation").status_code == 401

    def test_list_on_hand_requires_auth(self, client):
        assert client.get("/api/inventory/on-hand").status_code == 401

    def test_transfer_stock_requires_auth(self, client):
        assert client.post("/api/inventory/transfer", json={}).status_code == 401

    def test_cross_transfer_stock_requires_auth(self, client):
        assert client.post("/api/inventory/transfer-cross", json={}).status_code == 401


# ── Supplier quotes ──────────────────────────────────────────────────


class TestSupplierQuotesAuthEnforcement:
    def test_create_quote_requires_auth(self, client):
        assert client.post("/api/supplier-quotes/", json={}).status_code == 401

    def test_delete_quote_requires_auth(self, client):
        assert client.delete("/api/supplier-quotes/1").status_code == 401


# ── Users ────────────────────────────────────────────────────────────


class TestUsersAuthEnforcement:
    def test_get_me_requires_auth(self, client):
        assert client.get("/api/users/me").status_code == 401

    def test_create_user_requires_auth(self, client):
        assert client.post("/api/users/", json={}).status_code == 401


# ── Auth (protected endpoints only) ─────────────────────────────────


class TestAuthProtectedEndpoints:
    def test_get_auth_me_requires_auth(self, client):
        assert client.get("/api/auth/me").status_code == 401

    def test_change_password_requires_auth(self, client):
        assert client.post("/api/auth/change-password", json={}).status_code == 401


# ── Public endpoints should NOT require auth ─────────────────────────


class TestPublicEndpoints:
    """Verify that public endpoints do NOT go through get_current_user."""

    def test_health_is_public(self, client):
        assert client.get("/api/health").status_code == 200

    def test_login_is_public(self, client):
        from unittest.mock import MagicMock, patch

        mock_user = MagicMock(id="uid", email="a@b.com")
        mock_session = MagicMock(access_token="t", refresh_token="r", expires_in=3600, token_type="bearer")
        with patch("app.routers.auth.supabase_auth") as mock_auth:
            mock_auth.auth.sign_in_with_password.return_value = MagicMock(user=mock_user, session=mock_session)
            resp = client.post("/api/auth/login", json={"email": "a@b.com", "password": "x"})
        assert resp.status_code == 200

    def test_signup_is_public(self, client):
        from unittest.mock import MagicMock, patch

        with patch("app.routers.auth.supabase_auth") as mock_auth:
            mock_auth.auth.sign_up.return_value = MagicMock(user=MagicMock(id="uid", email="a@b.com"), session=None)
            resp = client.post("/api/auth/signup", json={"email": "a@b.com", "password": "pass123"})
        assert resp.status_code == 200
