"""Happy-path and behaviour tests for every API endpoint.

Each endpoint is tested for correct HTTP status code, correct response
shape, and correct delegation to the service layer.  Services are
mocked so no database or network calls are made.
"""

from unittest.mock import MagicMock, patch

from app.errors import NotFoundError
from app.middleware.auth import UserProfile

# ── helpers ──────────────────────────────────────────────────────────

PAGINATED_EMPTY = {"data": [], "total": 0}


def _paginated(items: list) -> dict:
    return {"data": items, "total": len(items)}


# =====================================================================
# Auth endpoints
# =====================================================================


class TestAuthLogin:
    def test_login_returns_200_with_user_and_session(self, client):
        mock_user = MagicMock(id="uid-1", email="a@b.com")
        mock_session = MagicMock(
            access_token="tok",
            refresh_token="rtok",
            expires_in=3600,
            token_type="bearer",
        )
        with patch("app.routers.auth.supabase_auth") as mock_auth:
            mock_auth.auth.sign_in_with_password.return_value = MagicMock(user=mock_user, session=mock_session)
            resp = client.post(
                "/api/auth/login",
                json={"email": "a@b.com", "password": "secret123"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["user"]["id"] == "uid-1"
        assert body["user"]["email"] == "a@b.com"
        assert body["session"]["access_token"] == "tok"
        assert body["session"]["refresh_token"] == "rtok"
        assert body["session"]["expires_in"] == 3600
        assert body["session"]["token_type"] == "bearer"

    def test_login_returns_401_on_bad_credentials(self, client):
        with patch("app.routers.auth.supabase_auth") as mock_auth:
            mock_auth.auth.sign_in_with_password.side_effect = Exception("Invalid")
            resp = client.post(
                "/api/auth/login",
                json={"email": "a@b.com", "password": "wrong"},
            )
        assert resp.status_code == 401

    def test_login_returns_401_when_user_is_none(self, client):
        with patch("app.routers.auth.supabase_auth") as mock_auth:
            mock_auth.auth.sign_in_with_password.return_value = MagicMock(user=None, session=None)
            resp = client.post(
                "/api/auth/login",
                json={"email": "a@b.com", "password": "bad"},
            )
        assert resp.status_code == 401


class TestAuthSignup:
    def test_signup_returns_200_with_user(self, client):
        mock_user = MagicMock(id="uid-2", email="new@b.com")
        mock_session = MagicMock(
            access_token="tok2",
            refresh_token="rtok2",
            expires_in=3600,
            token_type="bearer",
        )
        with patch("app.routers.auth.supabase_auth") as mock_auth:
            mock_auth.auth.sign_up.return_value = MagicMock(user=mock_user, session=mock_session)
            resp = client.post(
                "/api/auth/signup",
                json={"email": "new@b.com", "password": "pass123"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["user"]["id"] == "uid-2"
        assert body["session"]["access_token"] == "tok2"

    def test_signup_returns_null_session_when_confirmation_required(self, client):
        mock_user = MagicMock(id="uid-3", email="x@b.com")
        with patch("app.routers.auth.supabase_auth") as mock_auth:
            mock_auth.auth.sign_up.return_value = MagicMock(user=mock_user, session=None)
            resp = client.post(
                "/api/auth/signup",
                json={"email": "x@b.com", "password": "pass123"},
            )
        assert resp.status_code == 200
        assert resp.json()["session"] is None

    def test_signup_returns_400_on_failure(self, client):
        with patch("app.routers.auth.supabase_auth") as mock_auth:
            mock_auth.auth.sign_up.side_effect = Exception("Duplicate")
            resp = client.post(
                "/api/auth/signup",
                json={"email": "dup@b.com", "password": "pass123"},
            )
        assert resp.status_code == 400

    def test_signup_returns_400_when_user_none(self, client):
        with patch("app.routers.auth.supabase_auth") as mock_auth:
            mock_auth.auth.sign_up.return_value = MagicMock(user=None)
            resp = client.post(
                "/api/auth/signup",
                json={"email": "x@b.com", "password": "pass123"},
            )
        assert resp.status_code == 400


class TestAuthMe:
    def test_get_me_with_profile(self, authed_client):
        resp = authed_client.get("/api/auth/me")
        assert resp.status_code == 200
        body = resp.json()
        assert body["user"]["id"] == "auth-user-id-123"
        assert body["user"]["email"] == "test@example.com"
        assert body["profile"]["user_id"] == 456
        assert body["profile"]["name"] == "Test User"
        assert body["profile"]["email_address"] == "test@example.com"

    def test_get_me_without_profile(self, unauthed_client):
        resp = unauthed_client.get("/api/auth/me")
        assert resp.status_code == 200
        body = resp.json()
        assert body["user"]["id"] == "auth-user-id-123"
        assert body["profile"] is None


class TestAuthChangePassword:
    def test_change_password_success(self, authed_client):
        with patch("app.routers.auth.supabase_auth"):
            resp = authed_client.post(
                "/api/auth/change-password",
                json={"current_password": "old123", "new_password": "new123"},
            )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_change_password_wrong_current(self, authed_client):
        with patch("app.routers.auth.supabase_auth") as mock_auth:
            mock_auth.auth.sign_in_with_password.side_effect = Exception("Bad creds")
            resp = authed_client.post(
                "/api/auth/change-password",
                json={"current_password": "wrong", "new_password": "new123"},
            )
        assert resp.status_code == 400

    def test_change_password_update_failure(self, authed_client):
        with patch("app.routers.auth.supabase_auth") as mock_auth:
            mock_auth.auth.admin.update_user_by_id.side_effect = Exception("Weak")
            resp = authed_client.post(
                "/api/auth/change-password",
                json={"current_password": "old123", "new_password": "new123"},
            )
        assert resp.status_code == 400


# =====================================================================
# Sales endpoints
# =====================================================================


class TestSaleEndpoints:
    SALE_ROW = {
        "sale_id": 1,
        "status": "active",
        "customer": {"id": 1, "name": "Acme"},
        "channel": {"id": 1, "name": "eBay"},
        "created_at": "2026-04-01T00:00:00",
    }

    def test_list_sales_returns_200(self, authed_client):
        with patch("app.routers.sales.service") as svc:
            svc.list_sales.return_value = _paginated([self.SALE_ROW])
            resp = authed_client.get("/api/sales/")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body and "total" in body
        assert body["total"] == 1

    def test_list_sales_passes_default_pagination(self, authed_client):
        with patch("app.routers.sales.service") as svc:
            svc.list_sales.return_value = PAGINATED_EMPTY
            authed_client.get("/api/sales/")
        svc.list_sales.assert_called_once_with(50, 0, None)

    def test_list_sales_passes_custom_pagination(self, authed_client):
        with patch("app.routers.sales.service") as svc:
            svc.list_sales.return_value = PAGINATED_EMPTY
            authed_client.get("/api/sales/?limit=10&offset=5")
        svc.list_sales.assert_called_once_with(10, 5, None)

    def test_list_sales_with_search(self, authed_client):
        with patch("app.routers.sales.service") as svc:
            svc.list_sales.return_value = _paginated([self.SALE_ROW])
            resp = authed_client.get("/api/sales/?search=PART-1")
        svc.list_sales.assert_called_once_with(50, 0, "PART-1")
        assert resp.status_code == 200

    def test_get_sale_returns_200(self, authed_client):
        with patch("app.routers.sales.service") as svc:
            svc.get_sale.return_value = self.SALE_ROW
            resp = authed_client.get("/api/sales/1")
        assert resp.status_code == 200
        assert resp.json()["sale_id"] == 1
        svc.get_sale.assert_called_once_with(1)

    def test_get_sale_not_found(self, authed_client):
        with patch("app.routers.sales.service") as svc:
            svc.get_sale.side_effect = NotFoundError("Sale", "999")
            resp = authed_client.get("/api/sales/999")
        assert resp.status_code == 404

    def test_get_sale_lines_returns_200(self, authed_client):
        lines = [{"sale_line_id": 1, "item_id": "P1", "quantity": 2}]
        with patch("app.routers.sales.service") as svc:
            svc.get_sale_lines.return_value = lines
            resp = authed_client.get("/api/sales/1/lines")
        assert resp.status_code == 200
        assert resp.json() == lines
        svc.get_sale_lines.assert_called_once_with(1)

    def test_create_sale_returns_201(self, authed_client):
        with patch("app.routers.sales.service") as svc:
            svc.create_sale.return_value = {"sale_id": 10}
            resp = authed_client.post(
                "/api/sales/",
                json={
                    "sale": {},
                    "lines": [{"quantity": 1, "unit_price": 10.0, "currency_id": 1}],
                },
            )
        assert resp.status_code == 201
        assert resp.json()["sale_id"] == 10

    def test_create_sale_injects_user_id(self, authed_client):
        with patch("app.routers.sales.service") as svc:
            svc.create_sale.return_value = {"sale_id": 10}
            authed_client.post(
                "/api/sales/",
                json={
                    "sale": {},
                    "lines": [{"quantity": 1, "unit_price": 10.0, "currency_id": 1}],
                },
            )
        sale_data = svc.create_sale.call_args[0][0]
        assert sale_data["user_id"] == 456

    def test_void_sale_returns_success(self, authed_client):
        with patch("app.routers.sales.service") as svc:
            resp = authed_client.post("/api/sales/1/void", json={"reason": "mistake"})
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        svc.void_sale.assert_called_once_with(1, 456, "mistake")

    def test_void_sale_without_reason(self, authed_client):
        with patch("app.routers.sales.service") as svc:
            resp = authed_client.post("/api/sales/1/void", json={})
        assert resp.status_code == 200
        svc.void_sale.assert_called_once_with(1, 456, None)


# =====================================================================
# Receipts endpoints
# =====================================================================


class TestReceiptEndpoints:
    RECEIPT_ROW = {
        "receipt_id": 1,
        "status": "active",
        "supplier": {"id": 1, "name": "Supplier A"},
        "created_at": "2026-04-01T00:00:00",
    }

    def test_list_receipts_returns_200(self, authed_client):
        with patch("app.routers.receipts.service") as svc:
            svc.list_receipts.return_value = _paginated([self.RECEIPT_ROW])
            resp = authed_client.get("/api/receipts/")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body and "total" in body

    def test_list_receipts_passes_default_pagination(self, authed_client):
        with patch("app.routers.receipts.service") as svc:
            svc.list_receipts.return_value = PAGINATED_EMPTY
            authed_client.get("/api/receipts/")
        svc.list_receipts.assert_called_once_with(50, 0, None)

    def test_list_receipts_passes_custom_pagination(self, authed_client):
        with patch("app.routers.receipts.service") as svc:
            svc.list_receipts.return_value = PAGINATED_EMPTY
            authed_client.get("/api/receipts/?limit=25&offset=10")
        svc.list_receipts.assert_called_once_with(25, 10, None)

    def test_list_receipts_with_search(self, authed_client):
        with patch("app.routers.receipts.service") as svc:
            svc.list_receipts.return_value = _paginated([self.RECEIPT_ROW])
            resp = authed_client.get("/api/receipts/?search=PART-2")
        svc.list_receipts.assert_called_once_with(50, 0, "PART-2")
        assert resp.status_code == 200

    def test_get_receipt_returns_200(self, authed_client):
        with patch("app.routers.receipts.service") as svc:
            svc.get_receipt.return_value = self.RECEIPT_ROW
            resp = authed_client.get("/api/receipts/1")
        assert resp.status_code == 200
        assert resp.json()["receipt_id"] == 1
        svc.get_receipt.assert_called_once_with(1)

    def test_get_receipt_not_found(self, authed_client):
        with patch("app.routers.receipts.service") as svc:
            svc.get_receipt.side_effect = NotFoundError("Receipt", "999")
            resp = authed_client.get("/api/receipts/999")
        assert resp.status_code == 404

    def test_get_receipt_lines_returns_200(self, authed_client):
        lines = [{"receipt_line_id": 1, "item_id": "P1", "quantity": 5}]
        with patch("app.routers.receipts.service") as svc:
            svc.get_receipt_lines.return_value = lines
            resp = authed_client.get("/api/receipts/1/lines")
        assert resp.status_code == 200
        assert resp.json() == lines
        svc.get_receipt_lines.assert_called_once_with(1)

    def test_create_receipt_returns_201(self, authed_client):
        with patch("app.routers.receipts.service") as svc:
            svc.create_receipt.return_value = {"receipt_id": 10}
            resp = authed_client.post(
                "/api/receipts/",
                json={
                    "receipt": {},
                    "lines": [{"quantity": 5, "unit_price": 20.0, "currency_id": 1}],
                },
            )
        assert resp.status_code == 201
        assert resp.json()["receipt_id"] == 10

    def test_create_receipt_injects_user_id(self, authed_client):
        with patch("app.routers.receipts.service") as svc:
            svc.create_receipt.return_value = {"receipt_id": 10}
            authed_client.post(
                "/api/receipts/",
                json={
                    "receipt": {},
                    "lines": [{"quantity": 5, "unit_price": 20.0, "currency_id": 1}],
                },
            )
        receipt_data = svc.create_receipt.call_args[0][0]
        assert receipt_data["user_id"] == 456

    def test_void_receipt_returns_success(self, authed_client):
        with patch("app.routers.receipts.service") as svc:
            resp = authed_client.post("/api/receipts/1/void", json={"reason": "wrong supplier"})
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        svc.void_receipt.assert_called_once_with(1, 456, "wrong supplier")

    def test_void_receipt_without_reason(self, authed_client):
        with patch("app.routers.receipts.service") as svc:
            resp = authed_client.post("/api/receipts/1/void", json={})
        assert resp.status_code == 200
        svc.void_receipt.assert_called_once_with(1, 456, None)


# =====================================================================
# Items endpoints
# =====================================================================


class TestItemEndpoints:
    ITEM_ROW = {
        "id": 1,
        "item_id": "PART-001",
        "description": "Widget",
        "category_id": 1,
    }

    def test_list_items_returns_200(self, authed_client):
        with patch("app.routers.items.service") as svc:
            svc.list_items.return_value = _paginated([self.ITEM_ROW])
            resp = authed_client.get("/api/items/")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body and "total" in body

    def test_list_items_passes_default_pagination(self, authed_client):
        with patch("app.routers.items.service") as svc:
            svc.list_items.return_value = PAGINATED_EMPTY
            authed_client.get("/api/items/")
        svc.list_items.assert_called_once_with(1000, 0)

    def test_list_items_passes_custom_pagination(self, authed_client):
        with patch("app.routers.items.service") as svc:
            svc.list_items.return_value = PAGINATED_EMPTY
            authed_client.get("/api/items/?limit=50&offset=10")
        svc.list_items.assert_called_once_with(50, 10)

    def test_search_items_returns_200(self, authed_client):
        with patch("app.routers.items.service") as svc:
            svc.search_items.return_value = _paginated([self.ITEM_ROW])
            resp = authed_client.get("/api/items/search?q=PART")
        assert resp.status_code == 200

    def test_search_items_passes_query_and_defaults(self, authed_client):
        with patch("app.routers.items.service") as svc:
            svc.search_items.return_value = PAGINATED_EMPTY
            authed_client.get("/api/items/search?q=PART")
        svc.search_items.assert_called_once_with("PART", 1000, 0, in_stock=False)

    def test_search_items_with_in_stock(self, authed_client):
        with patch("app.routers.items.service") as svc:
            svc.search_items.return_value = PAGINATED_EMPTY
            authed_client.get("/api/items/search?q=PART&in_stock=true")
        svc.search_items.assert_called_once_with("PART", 1000, 0, in_stock=True)

    def test_search_items_custom_pagination(self, authed_client):
        with patch("app.routers.items.service") as svc:
            svc.search_items.return_value = PAGINATED_EMPTY
            authed_client.get("/api/items/search?q=X&limit=20&offset=5")
        svc.search_items.assert_called_once_with("X", 20, 5, in_stock=False)

    def test_get_item_returns_200(self, authed_client):
        with patch("app.routers.items.service") as svc:
            svc.get_item.return_value = self.ITEM_ROW
            resp = authed_client.get("/api/items/1")
        assert resp.status_code == 200
        assert resp.json()["item_id"] == "PART-001"
        svc.get_item.assert_called_once_with(1)

    def test_get_item_not_found(self, authed_client):
        with patch("app.routers.items.service") as svc:
            svc.get_item.side_effect = NotFoundError("Item", "999")
            resp = authed_client.get("/api/items/999")
        assert resp.status_code == 404

    def test_get_item_quotes_returns_200(self, authed_client):
        quotes = [{"quote_id": 1, "supplier_id": 1, "cost": 5.50}]
        with patch("app.routers.items.service") as svc:
            svc.get_item_quotes.return_value = quotes
            resp = authed_client.get("/api/items/1/quotes")
        assert resp.status_code == 200
        assert resp.json() == quotes

    def test_get_item_inventory_returns_200(self, authed_client):
        inv = [{"stock_id": 1, "location": "WH-A", "quantity": 10}]
        with patch("app.routers.items.service") as svc:
            svc.get_item_inventory.return_value = inv
            resp = authed_client.get("/api/items/1/inventory")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_get_item_receipts_returns_200(self, authed_client):
        with patch("app.routers.items.service") as svc:
            svc.get_item_receipts.return_value = []
            resp = authed_client.get("/api/items/1/receipts")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_item_sales_returns_200(self, authed_client):
        with patch("app.routers.items.service") as svc:
            svc.get_item_sales.return_value = []
            resp = authed_client.get("/api/items/1/sales")
        assert resp.status_code == 200

    def test_create_item_returns_201(self, authed_client):
        with patch("app.routers.items.service") as svc:
            svc.create_item.return_value = {"id": 5, "item_id": "NEW-1"}
            resp = authed_client.post("/api/items/", json={"item_id": "NEW-1"})
        assert resp.status_code == 201
        assert resp.json()["item_id"] == "NEW-1"

    def test_create_item_passes_data(self, authed_client):
        with patch("app.routers.items.service") as svc:
            svc.create_item.return_value = {"id": 5}
            authed_client.post(
                "/api/items/",
                json={"item_id": "NEW-1", "description": "A widget"},
            )
        data = svc.create_item.call_args[0][0]
        assert data["item_id"] == "NEW-1"
        assert data["description"] == "A widget"

    def test_update_item_returns_200(self, authed_client):
        with patch("app.routers.items.service") as svc:
            svc.update_item.return_value = {"id": 1, "description": "Updated"}
            resp = authed_client.put("/api/items/1", json={"description": "Updated"})
        assert resp.status_code == 200

    def test_update_item_excludes_none_fields(self, authed_client):
        with patch("app.routers.items.service") as svc:
            svc.update_item.return_value = {"id": 1}
            authed_client.put("/api/items/1", json={"description": "Up"})
        data = svc.update_item.call_args[0][1]
        assert "description" in data
        assert "item_id" not in data
        assert "category_id" not in data

    def test_delete_item_returns_success(self, authed_client):
        with patch("app.routers.items.service") as svc:
            resp = authed_client.delete("/api/items/1")
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        svc.delete_item.assert_called_once_with(1)


# =====================================================================
# Categories endpoints
# =====================================================================


class TestCategoryEndpoints:
    def test_list_categories_returns_200(self, authed_client):
        with patch("app.routers.categories.service") as svc:
            svc.list_categories.return_value = _paginated([{"id": 1, "name": "Tools"}])
            resp = authed_client.get("/api/categories/")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_list_categories_passes_default_pagination(self, authed_client):
        with patch("app.routers.categories.service") as svc:
            svc.list_categories.return_value = PAGINATED_EMPTY
            authed_client.get("/api/categories/")
        svc.list_categories.assert_called_once_with(5000, 0)

    def test_list_categories_passes_custom_pagination(self, authed_client):
        with patch("app.routers.categories.service") as svc:
            svc.list_categories.return_value = PAGINATED_EMPTY
            authed_client.get("/api/categories/?limit=10&offset=5")
        svc.list_categories.assert_called_once_with(10, 5)

    def test_create_category_returns_201(self, authed_client):
        with patch("app.routers.categories.service") as svc:
            svc.create_category.return_value = {"id": 2, "name": "Electronics"}
            resp = authed_client.post("/api/categories/", json={"name": "Electronics"})
        assert resp.status_code == 201
        assert resp.json()["name"] == "Electronics"

    def test_create_category_passes_data(self, authed_client):
        with patch("app.routers.categories.service") as svc:
            svc.create_category.return_value = {"id": 2}
            authed_client.post("/api/categories/", json={"name": "Parts"})
        svc.create_category.assert_called_once_with({"name": "Parts"})

    def test_delete_category_returns_success(self, authed_client):
        with patch("app.routers.categories.service") as svc:
            resp = authed_client.delete("/api/categories/1")
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        svc.delete_category.assert_called_once_with(1)


# =====================================================================
# Locations endpoints
# =====================================================================


class TestLocationEndpoints:
    def test_list_locations_returns_200(self, authed_client):
        with patch("app.routers.locations.service") as svc:
            svc.list_locations.return_value = _paginated([{"id": 1, "code": "WH-A"}])
            resp = authed_client.get("/api/locations/")
        assert resp.status_code == 200

    def test_list_locations_passes_default_pagination(self, authed_client):
        with patch("app.routers.locations.service") as svc:
            svc.list_locations.return_value = PAGINATED_EMPTY
            authed_client.get("/api/locations/")
        svc.list_locations.assert_called_once_with(5000, 0)

    def test_list_locations_passes_custom_pagination(self, authed_client):
        with patch("app.routers.locations.service") as svc:
            svc.list_locations.return_value = PAGINATED_EMPTY
            authed_client.get("/api/locations/?limit=10&offset=2")
        svc.list_locations.assert_called_once_with(10, 2)

    def test_create_location_returns_201(self, authed_client):
        with patch("app.routers.locations.service") as svc:
            svc.create_location.return_value = {"id": 2, "code": "WH-B"}
            resp = authed_client.post("/api/locations/", json={"code": "WH-B"})
        assert resp.status_code == 201
        assert resp.json()["code"] == "WH-B"

    def test_create_location_passes_data(self, authed_client):
        with patch("app.routers.locations.service") as svc:
            svc.create_location.return_value = {"id": 2}
            authed_client.post("/api/locations/", json={"code": "WH-C"})
        svc.create_location.assert_called_once_with({"code": "WH-C"})

    def test_delete_location_returns_success(self, authed_client):
        with patch("app.routers.locations.service") as svc:
            resp = authed_client.delete("/api/locations/1")
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        svc.delete_location.assert_called_once_with(1)


# =====================================================================
# Suppliers endpoints
# =====================================================================


class TestSupplierEndpoints:
    def test_list_suppliers_returns_200(self, authed_client):
        with patch("app.routers.suppliers.service") as svc:
            svc.list_suppliers.return_value = _paginated([{"id": 1, "name": "Acme"}])
            resp = authed_client.get("/api/suppliers/")
        assert resp.status_code == 200

    def test_list_suppliers_passes_default_pagination(self, authed_client):
        with patch("app.routers.suppliers.service") as svc:
            svc.list_suppliers.return_value = PAGINATED_EMPTY
            authed_client.get("/api/suppliers/")
        svc.list_suppliers.assert_called_once_with(5000, 0)

    def test_create_supplier_returns_201(self, authed_client):
        with patch("app.routers.suppliers.service") as svc:
            svc.create_supplier.return_value = {"id": 2, "name": "Beta"}
            resp = authed_client.post("/api/suppliers/", json={"name": "Beta"})
        assert resp.status_code == 201
        assert resp.json()["name"] == "Beta"

    def test_create_supplier_passes_full_data(self, authed_client):
        full = {"name": "Gamma", "email": "g@test.com", "phone": "555", "address": "1 St"}
        with patch("app.routers.suppliers.service") as svc:
            svc.create_supplier.return_value = {"id": 3}
            authed_client.post("/api/suppliers/", json=full)
        data = svc.create_supplier.call_args[0][0]
        assert data["name"] == "Gamma"
        assert data["email"] == "g@test.com"

    def test_delete_supplier_returns_success(self, authed_client):
        with patch("app.routers.suppliers.service") as svc:
            resp = authed_client.delete("/api/suppliers/1")
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        svc.delete_supplier.assert_called_once_with(1)


# =====================================================================
# Customers endpoints
# =====================================================================


class TestCustomerEndpoints:
    def test_list_customers_returns_200(self, authed_client):
        with patch("app.routers.customers.service") as svc:
            svc.list_customers.return_value = _paginated([{"id": 1, "name": "Client A"}])
            resp = authed_client.get("/api/customers/")
        assert resp.status_code == 200

    def test_list_customers_passes_default_pagination(self, authed_client):
        with patch("app.routers.customers.service") as svc:
            svc.list_customers.return_value = PAGINATED_EMPTY
            authed_client.get("/api/customers/")
        svc.list_customers.assert_called_once_with(5000, 0)

    def test_list_customers_passes_custom_pagination(self, authed_client):
        with patch("app.routers.customers.service") as svc:
            svc.list_customers.return_value = PAGINATED_EMPTY
            authed_client.get("/api/customers/?limit=100&offset=50")
        svc.list_customers.assert_called_once_with(100, 50)

    def test_create_customer_returns_201(self, authed_client):
        with patch("app.routers.customers.service") as svc:
            svc.create_customer.return_value = {"id": 2, "name": "Client B"}
            resp = authed_client.post("/api/customers/", json={"name": "Client B"})
        assert resp.status_code == 201
        assert resp.json()["name"] == "Client B"

    def test_create_customer_passes_full_data(self, authed_client):
        full = {"name": "Client C", "email": "c@test.com", "phone": "555", "city": "London"}
        with patch("app.routers.customers.service") as svc:
            svc.create_customer.return_value = {"id": 3}
            authed_client.post("/api/customers/", json=full)
        data = svc.create_customer.call_args[0][0]
        assert data["name"] == "Client C"
        assert data["city"] == "London"


# =====================================================================
# Channels endpoints
# =====================================================================


class TestChannelEndpoints:
    def test_list_channels_returns_200(self, authed_client):
        with patch("app.routers.channels.service") as svc:
            svc.list_channels.return_value = _paginated([{"id": 1, "name": "eBay"}])
            resp = authed_client.get("/api/channels/")
        assert resp.status_code == 200

    def test_list_channels_passes_default_pagination(self, authed_client):
        with patch("app.routers.channels.service") as svc:
            svc.list_channels.return_value = PAGINATED_EMPTY
            authed_client.get("/api/channels/")
        svc.list_channels.assert_called_once_with(5000, 0)


# =====================================================================
# Currencies endpoints
# =====================================================================


class TestCurrencyEndpoints:
    def test_list_currencies_returns_200(self, authed_client):
        with patch("app.routers.currencies.service") as svc:
            svc.list_currencies.return_value = _paginated([{"id": 1, "code": "GBP"}])
            resp = authed_client.get("/api/currencies/")
        assert resp.status_code == 200

    def test_list_currencies_passes_default_pagination(self, authed_client):
        with patch("app.routers.currencies.service") as svc:
            svc.list_currencies.return_value = PAGINATED_EMPTY
            authed_client.get("/api/currencies/")
        svc.list_currencies.assert_called_once_with(5000, 0)


# =====================================================================
# Inventory endpoints
# =====================================================================


class TestInventoryEndpoints:
    def test_list_movements_returns_200(self, authed_client):
        with patch("app.routers.inventory.service") as svc:
            svc.list_movements.return_value = _paginated([{"transfer_id": 1, "quantity": 5}])
            resp = authed_client.get("/api/inventory/movements")
        assert resp.status_code == 200

    def test_list_movements_passes_default_pagination(self, authed_client):
        with patch("app.routers.inventory.service") as svc:
            svc.list_movements.return_value = PAGINATED_EMPTY
            authed_client.get("/api/inventory/movements")
        svc.list_movements.assert_called_once_with(50, 0)

    def test_list_movements_passes_custom_pagination(self, authed_client):
        with patch("app.routers.inventory.service") as svc:
            svc.list_movements.return_value = PAGINATED_EMPTY
            authed_client.get("/api/inventory/movements?limit=10&offset=5")
        svc.list_movements.assert_called_once_with(10, 5)

    def test_list_on_hand_returns_200(self, authed_client):
        on_hand = [{"item_id": "P1", "location": "WH-A", "quantity": 10}]
        with patch("app.routers.inventory.service") as svc:
            svc.list_on_hand.return_value = on_hand
            resp = authed_client.get("/api/inventory/on-hand")
        assert resp.status_code == 200
        assert resp.json() == on_hand

    def test_transfer_stock_returns_201(self, authed_client):
        with patch("app.routers.inventory.service") as svc:
            svc.transfer_stock.return_value = {"transfer_id": 1}
            resp = authed_client.post(
                "/api/inventory/transfer",
                json={"from_stock_id": 1, "to_location_id": 2, "quantity": 5},
            )
        assert resp.status_code == 201

    def test_transfer_stock_passes_data_and_user_id(self, authed_client):
        with patch("app.routers.inventory.service") as svc:
            svc.transfer_stock.return_value = {"transfer_id": 1}
            authed_client.post(
                "/api/inventory/transfer",
                json={
                    "from_stock_id": 10,
                    "to_location_id": 20,
                    "quantity": 3,
                    "notes": "Restock",
                },
            )
        svc.transfer_stock.assert_called_once_with(
            from_stock_id=10,
            to_location_id=20,
            quantity=3,
            user_id=456,
            notes="Restock",
        )

    def test_transfer_stock_without_notes(self, authed_client):
        with patch("app.routers.inventory.service") as svc:
            svc.transfer_stock.return_value = {"transfer_id": 2}
            authed_client.post(
                "/api/inventory/transfer",
                json={"from_stock_id": 1, "to_location_id": 2, "quantity": 1},
            )
        svc.transfer_stock.assert_called_once_with(
            from_stock_id=1,
            to_location_id=2,
            quantity=1,
            user_id=456,
            notes=None,
        )


# =====================================================================
# Supplier quotes endpoints
# =====================================================================


class TestSupplierQuoteEndpoints:
    QUOTE_BODY = {
        "item_id": 1,
        "supplier_id": 2,
        "cost": 12.50,
        "currency_id": 1,
    }

    def test_create_quote_returns_201(self, authed_client):
        with patch("app.routers.supplier_quotes.service") as svc:
            svc.create_quote.return_value = {"id": 1, **self.QUOTE_BODY}
            resp = authed_client.post("/api/supplier-quotes/", json=self.QUOTE_BODY)
        assert resp.status_code == 201

    def test_create_quote_excludes_note_field(self, authed_client):
        body_with_note = {**self.QUOTE_BODY, "note": "Best price"}
        with patch("app.routers.supplier_quotes.service") as svc:
            svc.create_quote.return_value = {"id": 1}
            authed_client.post("/api/supplier-quotes/", json=body_with_note)
        data = svc.create_quote.call_args[0][0]
        assert "note" not in data
        assert data["item_id"] == 1

    def test_create_quote_passes_optional_datetime(self, authed_client):
        body = {**self.QUOTE_BODY, "date_time": "2026-04-01T12:00:00"}
        with patch("app.routers.supplier_quotes.service") as svc:
            svc.create_quote.return_value = {"id": 1}
            authed_client.post("/api/supplier-quotes/", json=body)
        data = svc.create_quote.call_args[0][0]
        assert data["date_time"] == "2026-04-01T12:00:00"

    def test_delete_quote_returns_success(self, authed_client):
        with patch("app.routers.supplier_quotes.service") as svc:
            resp = authed_client.delete("/api/supplier-quotes/1")
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        svc.delete_quote.assert_called_once_with(1)


# =====================================================================
# Users endpoints
# =====================================================================


class TestUserEndpoints:
    def test_get_me_returns_profile_dict(self, authed_client):
        profile = UserProfile(user_id=456, first_name="Test", last_name="User", email="test@example.com")
        with patch("app.routers.users.service") as svc:
            svc.get_profile.return_value = profile
            resp = authed_client.get("/api/users/me")
        assert resp.status_code == 200
        body = resp.json()
        assert body["user_id"] == 456
        assert body["first_name"] == "Test"
        assert body["last_name"] == "User"

    def test_get_me_no_profile_returns_404(self, unauthed_client):
        with patch("app.routers.users.service") as svc:
            svc.get_profile.side_effect = NotFoundError("User profile", "current")
            resp = unauthed_client.get("/api/users/me")
        assert resp.status_code == 404

    def test_create_user_returns_201(self, authed_client):
        with patch("app.routers.users.service") as svc:
            svc.create_user.return_value = {"id": "new-uid", "email": "new@test.com"}
            resp = authed_client.post(
                "/api/users/",
                json={"email": "new@test.com", "password": "pass123"},
            )
        assert resp.status_code == 201
        assert resp.json()["user"]["email"] == "new@test.com"

    def test_create_user_passes_credentials(self, authed_client):
        with patch("app.routers.users.service") as svc:
            svc.create_user.return_value = {"id": "x"}
            authed_client.post(
                "/api/users/",
                json={"email": "x@test.com", "password": "secret123"},
            )
        svc.create_user.assert_called_once_with("x@test.com", "secret123")


# =====================================================================
# Health endpoint (already tested in test_health.py, but included
# here for completeness of the happy-path suite)
# =====================================================================


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
