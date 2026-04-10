"""Smoke tests that verify every endpoint can process a request without crashing.

Unlike test_router_responses.py (which tests specific behavior), these tests
verify the full FastAPI stack can handle requests without 500 errors from the
framework/middleware/serialization layer. Services are mocked to isolate
infrastructure issues like:
- Custom httpx clients breaking header serialization
- Middleware importing incompatible libraries
- Dependency injection failures
- Import-time errors in router modules

Each test mocks the service to return safe data and asserts no 500 response.
"""

from unittest.mock import patch

PAGINATED_EMPTY = {"data": [], "total": 0}
SAMPLE_ITEM = {"id": 1, "item_id": "TEST", "description": "Test"}
SAMPLE_RECORD = {"id": 1}


class TestGetEndpointSmoke:
    """Every GET endpoint must not return 500 when services return valid data."""

    def test_items_list(self, authed_client):
        with patch("app.routers.items.service") as svc:
            svc.list_items.return_value = PAGINATED_EMPTY
            assert authed_client.get("/api/items/").status_code != 500

    def test_items_search(self, authed_client):
        with patch("app.routers.items.service") as svc:
            svc.search_items.return_value = PAGINATED_EMPTY
            assert authed_client.get("/api/items/search?q=test").status_code != 500

    def test_items_by_search_id(self, authed_client):
        with patch("app.routers.items.service") as svc:
            svc.get_items_by_search_id.return_value = []
            assert authed_client.get("/api/items/by-search-id/test").status_code != 500

    def test_categories(self, authed_client):
        with patch("app.routers.categories.service") as svc:
            svc.list_categories.return_value = PAGINATED_EMPTY
            assert authed_client.get("/api/categories/").status_code != 500

    def test_locations(self, authed_client):
        with patch("app.routers.locations.service") as svc:
            svc.list_locations.return_value = PAGINATED_EMPTY
            assert authed_client.get("/api/locations/").status_code != 500

    def test_suppliers(self, authed_client):
        with patch("app.routers.suppliers.service") as svc:
            svc.list_suppliers.return_value = PAGINATED_EMPTY
            assert authed_client.get("/api/suppliers/").status_code != 500

    def test_channels(self, authed_client):
        with patch("app.routers.channels.service") as svc:
            svc.list_channels.return_value = PAGINATED_EMPTY
            assert authed_client.get("/api/channels/").status_code != 500

    def test_customers(self, authed_client):
        with patch("app.routers.customers.service") as svc:
            svc.list_customers.return_value = PAGINATED_EMPTY
            assert authed_client.get("/api/customers/").status_code != 500

    def test_currencies(self, authed_client):
        with patch("app.routers.currencies.service") as svc:
            svc.list_currencies.return_value = PAGINATED_EMPTY
            assert authed_client.get("/api/currencies/").status_code != 500

    def test_sales(self, authed_client):
        with patch("app.routers.sales.service") as svc:
            svc.list_sales.return_value = PAGINATED_EMPTY
            assert authed_client.get("/api/sales/").status_code != 500

    def test_receipts(self, authed_client):
        with patch("app.routers.receipts.service") as svc:
            svc.list_receipts.return_value = PAGINATED_EMPTY
            assert authed_client.get("/api/receipts/").status_code != 500

    def test_inventory_movements(self, authed_client):
        with patch("app.routers.inventory.service") as svc:
            svc.list_movements.return_value = PAGINATED_EMPTY
            assert authed_client.get("/api/inventory/movements").status_code != 500

    def test_inventory_on_hand(self, authed_client):
        with patch("app.routers.inventory.service") as svc:
            svc.list_on_hand.return_value = []
            assert authed_client.get("/api/inventory/on-hand").status_code != 500

    def test_inventory_stock_valuation(self, authed_client):
        with patch("app.routers.inventory.service") as svc:
            svc.stock_valuation.return_value = []
            assert authed_client.get("/api/inventory/stock-valuation").status_code != 500


class TestPostEndpointSmoke:
    """POST endpoints must not return 500 from framework/middleware issues."""

    def test_transfer(self, authed_client):
        with patch("app.routers.inventory.service") as svc:
            svc.transfer_stock.return_value = SAMPLE_RECORD
            resp = authed_client.post(
                "/api/inventory/transfer",
                json={"from_stock_id": 1, "to_location_id": 2, "quantity": 1},
            )
        assert resp.status_code != 500

    def test_cross_transfer(self, authed_client):
        with patch("app.routers.inventory.service") as svc:
            svc.cross_transfer_stock.return_value = SAMPLE_RECORD
            resp = authed_client.post(
                "/api/inventory/transfer-cross",
                json={
                    "from_item_id": 1,
                    "from_location_id": 2,
                    "to_item_id": 3,
                    "to_location_id": 4,
                    "quantity": 1,
                },
            )
        assert resp.status_code != 500
