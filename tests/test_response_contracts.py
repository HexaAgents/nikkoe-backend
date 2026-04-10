"""Response contract tests — verify the JSON shape the frontend depends on.

These tests act as a contract between backend and frontend.  If a
response shape changes, the corresponding test fails *before* the
change reaches production.  Each test mocks the service layer and
asserts exact key presence and value types.

Contracts are derived from the frontend types in
``nikkoe-frontend/src/types/domain.types.ts`` and
``nikkoe-frontend/src/types/api.types.ts``.
"""

from unittest.mock import patch

from app.middleware.auth import UserProfile

# ── helpers ──────────────────────────────────────────────────────────


def _assert_paginated(body: dict) -> None:
    """Assert the response matches PaginatedResponse<T> = { data, total }."""
    assert isinstance(body, dict), f"Expected dict, got {type(body)}"
    assert "data" in body, "Missing 'data' key"
    assert "total" in body, "Missing 'total' key"
    assert isinstance(body["data"], list), "'data' must be a list"
    assert isinstance(body["total"], int), "'total' must be an int"


def _assert_keys(obj: dict, required_keys: set) -> None:
    """Assert that *at least* the required keys are present."""
    missing = required_keys - set(obj.keys())
    assert not missing, f"Missing keys: {missing}"


# =====================================================================
# Sales contracts
# =====================================================================


SALE_FIXTURE = {
    "sale_id": 1,
    "status": "active",
    "created_at": "2026-04-01T10:00:00",
    "customer_id_id": 1,
    "channel_id_id": 1,
    "channel_ref": None,
    "note": None,
    "user_id": 456,
    "customer": {"id": 1, "name": "Acme"},
    "channel": {"id": 1, "name": "eBay"},
}


class TestSalesContract:
    def test_list_sales_returns_paginated_with_sale_objects(self, authed_client):
        with patch("app.routers.sales.service") as svc:
            svc.list_sales.return_value = {"data": [SALE_FIXTURE], "total": 1}
            resp = authed_client.get("/api/sales/")
        body = resp.json()
        _assert_paginated(body)
        sale = body["data"][0]
        _assert_keys(sale, {"sale_id", "status", "created_at"})

    def test_list_sales_empty_returns_paginated_zero(self, authed_client):
        with patch("app.routers.sales.service") as svc:
            svc.list_sales.return_value = {"data": [], "total": 0}
            resp = authed_client.get("/api/sales/")
        body = resp.json()
        _assert_paginated(body)
        assert body["data"] == []
        assert body["total"] == 0

    def test_get_sale_returns_sale_object(self, authed_client):
        with patch("app.routers.sales.service") as svc:
            svc.get_sale.return_value = SALE_FIXTURE
            resp = authed_client.get("/api/sales/1")
        sale = resp.json()
        _assert_keys(sale, {"sale_id", "status", "created_at"})

    def test_get_sale_lines_returns_list(self, authed_client):
        line = {"sale_line_id": 1, "item_id": 10, "quantity": 2, "unit_price": 5.0}
        with patch("app.routers.sales.service") as svc:
            svc.get_sale_lines.return_value = [line]
            resp = authed_client.get("/api/sales/1/lines")
        body = resp.json()
        assert isinstance(body, list)
        _assert_keys(body[0], {"quantity", "unit_price"})

    def test_create_sale_returns_object_with_sale_id(self, authed_client):
        with patch("app.routers.sales.service") as svc:
            svc.create_sale.return_value = {"sale_id": 10, "status": "active"}
            resp = authed_client.post(
                "/api/sales/",
                json={
                    "sale": {},
                    "lines": [{"quantity": 1, "unit_price": 10.0, "currency_id": 1}],
                },
            )
        assert resp.status_code == 201
        _assert_keys(resp.json(), {"sale_id"})

    def test_void_sale_returns_success_flag(self, authed_client):
        with patch("app.routers.sales.service"):
            resp = authed_client.post("/api/sales/1/void", json={})
        body = resp.json()
        assert body == {"success": True}


# =====================================================================
# Receipts contracts
# =====================================================================


RECEIPT_FIXTURE = {
    "receipt_id": 1,
    "status": "active",
    "created_at": "2026-04-01T10:00:00",
    "supplier_id": 1,
    "reference": "PO-001",
    "note": None,
    "user_id": 456,
    "supplier": {"id": 1, "name": "Supplier A"},
}


class TestReceiptsContract:
    def test_list_receipts_returns_paginated(self, authed_client):
        with patch("app.routers.receipts.service") as svc:
            svc.list_receipts.return_value = {"data": [RECEIPT_FIXTURE], "total": 1}
            resp = authed_client.get("/api/receipts/")
        body = resp.json()
        _assert_paginated(body)
        _assert_keys(body["data"][0], {"receipt_id", "status", "created_at"})

    def test_get_receipt_returns_receipt_object(self, authed_client):
        with patch("app.routers.receipts.service") as svc:
            svc.get_receipt.return_value = RECEIPT_FIXTURE
            resp = authed_client.get("/api/receipts/1")
        _assert_keys(resp.json(), {"receipt_id", "status", "created_at"})

    def test_get_receipt_lines_returns_list(self, authed_client):
        line = {"receipt_line_id": 1, "item_id": 10, "quantity": 5, "unit_price": 20.0}
        with patch("app.routers.receipts.service") as svc:
            svc.get_receipt_lines.return_value = [line]
            resp = authed_client.get("/api/receipts/1/lines")
        assert isinstance(resp.json(), list)

    def test_void_receipt_returns_success_flag(self, authed_client):
        with patch("app.routers.receipts.service"):
            resp = authed_client.post("/api/receipts/1/void", json={})
        assert resp.json() == {"success": True}


# =====================================================================
# Items contracts
# =====================================================================


ITEM_FIXTURE = {
    "id": 1,
    "item_id": "PART-001",
    "description": "Widget",
    "category_id": 1,
}


class TestItemsContract:
    def test_list_items_returns_paginated(self, authed_client):
        with patch("app.routers.items.service") as svc:
            svc.list_items.return_value = {"data": [ITEM_FIXTURE], "total": 1}
            resp = authed_client.get("/api/items/")
        body = resp.json()
        _assert_paginated(body)
        _assert_keys(body["data"][0], {"id", "item_id"})

    def test_search_items_returns_paginated(self, authed_client):
        with patch("app.routers.items.service") as svc:
            svc.search_items.return_value = {"data": [ITEM_FIXTURE], "total": 1}
            resp = authed_client.get("/api/items/search?q=PART")
        _assert_paginated(resp.json())

    def test_get_item_returns_item_object(self, authed_client):
        with patch("app.routers.items.service") as svc:
            svc.get_item.return_value = ITEM_FIXTURE
            resp = authed_client.get("/api/items/1")
        _assert_keys(resp.json(), {"id", "item_id"})

    def test_by_search_id_returns_plain_array(self, authed_client):
        items = [{"id": 1, "item_id": "AS-D", "search_id": "asd"}, {"id": 2, "item_id": "ASD", "search_id": "asd"}]
        with patch("app.routers.items.service") as svc:
            svc.get_items_by_search_id.return_value = items
            resp = authed_client.get("/api/items/by-search-id/asd")
        body = resp.json()
        assert isinstance(body, list), "by-search-id must return a plain array"
        assert len(body) == 2

    def test_delete_item_returns_success_flag(self, authed_client):
        with patch("app.routers.items.service"):
            resp = authed_client.delete("/api/items/1")
        assert resp.json() == {"success": True}


# =====================================================================
# Auth /me contract
# =====================================================================


class TestAuthMeContract:
    def test_auth_me_with_profile_has_correct_shape(self, authed_client):
        resp = authed_client.get("/api/auth/me")
        body = resp.json()
        _assert_keys(body, {"user", "profile"})
        _assert_keys(body["user"], {"id", "email"})
        assert body["profile"] is not None
        _assert_keys(body["profile"], {"user_id", "name", "email_address"})

    def test_auth_me_without_profile_returns_null_profile(self, unauthed_client):
        resp = unauthed_client.get("/api/auth/me")
        body = resp.json()
        _assert_keys(body, {"user", "profile"})
        assert body["profile"] is None


# =====================================================================
# Users /me contract
# =====================================================================


class TestUsersMeContract:
    def test_users_me_returns_profile_fields(self, authed_client):
        profile = UserProfile(user_id=456, first_name="Test", last_name="User", email="test@example.com")
        with patch("app.routers.users.service") as svc:
            svc.get_profile.return_value = profile
            resp = authed_client.get("/api/users/me")
        body = resp.json()
        _assert_keys(body, {"user_id", "first_name", "last_name", "email"})
        assert isinstance(body["user_id"], int)


# =====================================================================
# Lookup entities — all return { data, total }
# =====================================================================


class TestLookupEntityContracts:
    def test_categories_list_is_paginated(self, authed_client):
        with patch("app.routers.categories.service") as svc:
            svc.list_categories.return_value = {"data": [{"id": 1, "name": "Tools"}], "total": 1}
            resp = authed_client.get("/api/categories/")
        _assert_paginated(resp.json())

    def test_locations_list_is_paginated(self, authed_client):
        with patch("app.routers.locations.service") as svc:
            svc.list_locations.return_value = {"data": [{"id": 1, "code": "WH-A"}], "total": 1}
            resp = authed_client.get("/api/locations/")
        _assert_paginated(resp.json())

    def test_suppliers_list_is_paginated(self, authed_client):
        with patch("app.routers.suppliers.service") as svc:
            svc.list_suppliers.return_value = {"data": [{"id": 1, "name": "Acme"}], "total": 1}
            resp = authed_client.get("/api/suppliers/")
        _assert_paginated(resp.json())

    def test_customers_list_is_paginated(self, authed_client):
        with patch("app.routers.customers.service") as svc:
            svc.list_customers.return_value = {"data": [{"id": 1, "name": "Client"}], "total": 1}
            resp = authed_client.get("/api/customers/")
        _assert_paginated(resp.json())

    def test_channels_list_is_paginated(self, authed_client):
        with patch("app.routers.channels.service") as svc:
            svc.list_channels.return_value = {"data": [{"id": 1, "name": "eBay"}], "total": 1}
            resp = authed_client.get("/api/channels/")
        _assert_paginated(resp.json())

    def test_currencies_list_is_paginated(self, authed_client):
        with patch("app.routers.currencies.service") as svc:
            svc.list_currencies.return_value = {"data": [{"id": 1, "code": "GBP"}], "total": 1}
            resp = authed_client.get("/api/currencies/")
        _assert_paginated(resp.json())


# =====================================================================
# Inventory contract
# =====================================================================


class TestInventoryContract:
    def test_movements_is_paginated(self, authed_client):
        with patch("app.routers.inventory.service") as svc:
            svc.list_movements.return_value = {"data": [], "total": 0}
            resp = authed_client.get("/api/inventory/movements")
        _assert_paginated(resp.json())

    def test_stock_valuation_is_plain_array(self, authed_client):
        with patch("app.routers.inventory.service") as svc:
            svc.stock_valuation.return_value = []
            resp = authed_client.get("/api/inventory/stock-valuation")
        body = resp.json()
        assert isinstance(body, list), "stock-valuation must be a plain array"

    def test_on_hand_is_plain_array(self, authed_client):
        with patch("app.routers.inventory.service") as svc:
            svc.list_on_hand.return_value = [{"item_id": "P1", "quantity": 10}]
            resp = authed_client.get("/api/inventory/on-hand")
        body = resp.json()
        assert isinstance(body, list), "on-hand must be a plain array, not paginated"

    def test_cross_transfer_returns_object(self, authed_client):
        with patch("app.routers.inventory.service") as svc:
            svc.cross_transfer_stock.return_value = {"id": 1, "quantity": 5}
            resp = authed_client.post(
                "/api/inventory/transfer-cross",
                json={"from_item_id": 1, "from_location_id": 2, "to_item_id": 3, "to_location_id": 4, "quantity": 5},
            )
        assert resp.status_code == 201
        body = resp.json()
        assert "id" in body and "quantity" in body

    def test_transfer_returns_object(self, authed_client):
        with patch("app.routers.inventory.service") as svc:
            svc.transfer_stock.return_value = {"id": 1, "quantity": 3}
            resp = authed_client.post(
                "/api/inventory/transfer",
                json={"from_stock_id": 1, "to_location_id": 2, "quantity": 3},
            )
        assert resp.status_code == 201
        assert "id" in resp.json()


class TestAuthContract:
    def test_login_returns_user_and_session(self, client):
        from unittest.mock import MagicMock

        mock_user = MagicMock()
        mock_user.id = "uid"
        mock_user.email = "a@b.com"
        mock_session = MagicMock()
        mock_session.access_token = "tok"
        mock_session.refresh_token = "ref"
        mock_session.expires_in = 3600
        mock_session.token_type = "bearer"
        mock_resp = MagicMock()
        mock_resp.user = mock_user
        mock_resp.session = mock_session
        with patch("app.routers.auth.supabase_auth") as sa:
            sa.auth.sign_in_with_password.return_value = mock_resp
            resp = client.post("/api/auth/login", json={"email": "a@b.com", "password": "pass123"})
        body = resp.json()
        _assert_keys(body, {"user", "session"})
        _assert_keys(body["user"], {"id", "email"})
        _assert_keys(body["session"], {"access_token", "refresh_token", "expires_in", "token_type"})

    def test_refresh_returns_session(self, client):
        from unittest.mock import MagicMock

        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {
            "access_token": "new",
            "refresh_token": "new-ref",
            "expires_in": 3600,
            "token_type": "bearer",
        }
        with patch("app.routers.auth.httpx") as mh:
            mh.post.return_value = mock_resp
            resp = client.post("/api/auth/refresh", json={"refresh_token": "old"})
        body = resp.json()
        _assert_keys(body, {"session"})
        _assert_keys(body["session"], {"access_token", "refresh_token", "expires_in", "token_type"})


class TestItemSubResourceContracts:
    def test_item_quotes_is_array(self, authed_client):
        with patch("app.routers.items.service") as svc:
            svc.get_item_quotes.return_value = []
            resp = authed_client.get("/api/items/1/quotes")
        assert isinstance(resp.json(), list)

    def test_item_inventory_is_array(self, authed_client):
        with patch("app.routers.items.service") as svc:
            svc.get_item_inventory.return_value = []
            resp = authed_client.get("/api/items/1/inventory")
        assert isinstance(resp.json(), list)

    def test_item_receipts_is_array(self, authed_client):
        with patch("app.routers.items.service") as svc:
            svc.get_item_receipts.return_value = []
            resp = authed_client.get("/api/items/1/receipts")
        assert isinstance(resp.json(), list)

    def test_item_sales_is_array(self, authed_client):
        with patch("app.routers.items.service") as svc:
            svc.get_item_sales.return_value = []
            resp = authed_client.get("/api/items/1/sales")
        assert isinstance(resp.json(), list)

    def test_item_transfers_is_array(self, authed_client):
        with patch("app.routers.items.service") as svc:
            svc.get_item_transfers.return_value = []
            resp = authed_client.get("/api/items/1/transfers")
        assert isinstance(resp.json(), list)


class TestCreateEndpointContracts:
    def test_create_item_returns_object_with_id(self, authed_client):
        with patch("app.routers.items.service") as svc:
            svc.create_item.return_value = {"id": 1, "item_id": "NEW"}
            resp = authed_client.post("/api/items/", json={"item_id": "NEW"})
        assert resp.status_code == 201
        assert "id" in resp.json()

    def test_create_category_returns_object(self, authed_client):
        with patch("app.routers.categories.service") as svc:
            svc.create_category.return_value = {"id": 1, "name": "Cat"}
            resp = authed_client.post("/api/categories/", json={"name": "Cat"})
        assert resp.status_code == 201
        assert "id" in resp.json()

    def test_create_location_returns_object(self, authed_client):
        with patch("app.routers.locations.service") as svc:
            svc.create_location.return_value = {"id": 1, "code": "WH-A"}
            resp = authed_client.post("/api/locations/", json={"code": "WH-A"})
        assert resp.status_code == 201
        assert "id" in resp.json()

    def test_create_supplier_returns_object(self, authed_client):
        with patch("app.routers.suppliers.service") as svc:
            svc.create_supplier.return_value = {"id": 1, "name": "Sup"}
            resp = authed_client.post("/api/suppliers/", json={"name": "Sup"})
        assert resp.status_code == 201
        assert "id" in resp.json()

    def test_create_customer_returns_object(self, authed_client):
        with patch("app.routers.customers.service") as svc:
            svc.create_customer.return_value = {"id": 1, "name": "Cust"}
            resp = authed_client.post("/api/customers/", json={"name": "Cust"})
        assert resp.status_code == 201
        assert "id" in resp.json()

    def test_create_quote_returns_object(self, authed_client):
        with patch("app.routers.supplier_quotes.service") as svc:
            svc.create_quote.return_value = {"id": 1}
            resp = authed_client.post(
                "/api/supplier-quotes/",
                json={"item_id": 1, "supplier_id": 1, "cost": 5.0, "currency_id": 1},
            )
        assert resp.status_code == 201
        assert "id" in resp.json()


# =====================================================================
# Delete / void contracts — all must return { success: true }
# =====================================================================


class TestDeleteVoidContracts:
    def test_delete_category_contract(self, authed_client):
        with patch("app.routers.categories.service"):
            assert authed_client.delete("/api/categories/1").json() == {"success": True}

    def test_delete_location_contract(self, authed_client):
        with patch("app.routers.locations.service"):
            assert authed_client.delete("/api/locations/1").json() == {"success": True}

    def test_delete_supplier_contract(self, authed_client):
        with patch("app.routers.suppliers.service"):
            assert authed_client.delete("/api/suppliers/1").json() == {"success": True}

    def test_delete_supplier_quote_contract(self, authed_client):
        with patch("app.routers.supplier_quotes.service"):
            assert authed_client.delete("/api/supplier-quotes/1").json() == {"success": True}

    def test_delete_item_contract(self, authed_client):
        with patch("app.routers.items.service"):
            assert authed_client.delete("/api/items/1").json() == {"success": True}
