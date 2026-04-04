"""Tests for the service layer using mocked repositories.

Services contain the business logic of the application. By mocking the
repositories, we test that logic in isolation — no database, no network,
just pure Python. This makes tests fast and deterministic.
"""

import pytest
from unittest.mock import MagicMock

from app.errors import NotFoundError
from app.services.item import ItemService
from app.services.sale import SaleService
from app.services.receipt import ReceiptService
from app.services.category import CategoryService
from app.services.location import LocationService
from app.services.supplier import SupplierService
from app.services.customer import CustomerService
from app.services.channel import ChannelService
from app.services.inventory import InventoryService
from app.services.supplier_quote import SupplierQuoteService


# ---------------------------------------------------------------------------
# ItemService
# ---------------------------------------------------------------------------

class TestItemService:
    @pytest.fixture
    def repos(self):
        return {
            "repo": MagicMock(),
            "quote_repo": MagicMock(),
            "inventory_repo": MagicMock(),
            "receipt_repo": MagicMock(),
            "sale_repo": MagicMock(),
        }

    @pytest.fixture
    def service(self, repos):
        return ItemService(**repos)

    def test_list_items_delegates_to_repo(self, service, repos):
        repos["repo"].find_all.return_value = {"data": [], "total": 0}
        result = service.list_items(10, 0)
        repos["repo"].find_all.assert_called_once_with(10, 0)
        assert result == {"data": [], "total": 0}

    def test_list_items_uses_defaults(self, service, repos):
        repos["repo"].find_all.return_value = {"data": [], "total": 0}
        service.list_items()
        repos["repo"].find_all.assert_called_once_with(50, 0)

    def test_get_item_returns_item_when_found(self, service, repos):
        repos["repo"].find_by_id.return_value = {"item_id": "1", "part_number": "X"}
        result = service.get_item("1")
        assert result["part_number"] == "X"

    def test_get_item_raises_not_found(self, service, repos):
        repos["repo"].find_by_id.return_value = None
        with pytest.raises(NotFoundError) as exc_info:
            service.get_item("nonexistent")
        assert exc_info.value.status_code == 404
        assert "nonexistent" in exc_info.value.message

    def test_create_item_delegates_to_repo(self, service, repos):
        data = {"part_number": "NEW-1"}
        repos["repo"].create.return_value = {"item_id": "2", **data}
        result = service.create_item(data)
        repos["repo"].create.assert_called_once_with(data)
        assert result["part_number"] == "NEW-1"

    def test_update_item_delegates_to_repo(self, service, repos):
        repos["repo"].update.return_value = {"item_id": "1", "description": "Updated"}
        result = service.update_item("1", {"description": "Updated"})
        repos["repo"].update.assert_called_once_with("1", {"description": "Updated"})

    def test_delete_item_delegates_to_repo(self, service, repos):
        service.delete_item("1")
        repos["repo"].remove.assert_called_once_with("1")

    def test_get_item_quotes_delegates(self, service, repos):
        repos["quote_repo"].find_by_item_id.return_value = [{"quote_id": "q1"}]
        result = service.get_item_quotes("1")
        repos["quote_repo"].find_by_item_id.assert_called_once_with("1")
        assert len(result) == 1

    def test_get_item_inventory_delegates(self, service, repos):
        repos["inventory_repo"].find_by_item_id.return_value = []
        result = service.get_item_inventory("1")
        repos["inventory_repo"].find_by_item_id.assert_called_once_with("1")

    def test_get_item_receipts_delegates(self, service, repos):
        repos["receipt_repo"].find_by_item_id.return_value = []
        service.get_item_receipts("1")
        repos["receipt_repo"].find_by_item_id.assert_called_once_with("1")

    def test_get_item_sales_delegates(self, service, repos):
        repos["sale_repo"].find_by_item_id.return_value = []
        service.get_item_sales("1")
        repos["sale_repo"].find_by_item_id.assert_called_once_with("1")


# ---------------------------------------------------------------------------
# SaleService
# ---------------------------------------------------------------------------

class TestSaleService:
    @pytest.fixture
    def repo(self):
        return MagicMock()

    @pytest.fixture
    def service(self, repo):
        return SaleService(repo)

    def test_list_sales(self, service, repo):
        repo.find_all.return_value = {"data": [], "total": 0}
        result = service.list_sales(25, 10)
        repo.find_all.assert_called_once_with(25, 10)

    def test_get_sale_returns_sale(self, service, repo):
        repo.find_by_id.return_value = {"sale_id": "s1", "status": "active"}
        result = service.get_sale("s1")
        assert result["status"] == "active"

    def test_get_sale_raises_not_found(self, service, repo):
        repo.find_by_id.return_value = None
        with pytest.raises(NotFoundError):
            service.get_sale("missing")

    def test_get_sale_lines(self, service, repo):
        repo.find_lines.return_value = [{"sale_line_id": "sl1"}]
        result = service.get_sale_lines("s1")
        repo.find_lines.assert_called_once_with("s1")

    def test_create_sale(self, service, repo):
        sale_data = {"customer_name": "Test"}
        lines = [{"item_id": "i1", "quantity": 2}]
        repo.create.return_value = {"sale_id": "s1"}
        result = service.create_sale(sale_data, lines)
        repo.create.assert_called_once_with(sale_data, lines)

    def test_void_sale(self, service, repo):
        service.void_sale("s1", "user-1", "Mistake")
        repo.void_sale.assert_called_once_with("s1", "user-1", "Mistake")


# ---------------------------------------------------------------------------
# ReceiptService
# ---------------------------------------------------------------------------

class TestReceiptService:
    @pytest.fixture
    def repo(self):
        return MagicMock()

    @pytest.fixture
    def service(self, repo):
        return ReceiptService(repo)

    def test_list_receipts(self, service, repo):
        repo.find_all.return_value = {"data": [], "total": 0}
        service.list_receipts(50, 0)
        repo.find_all.assert_called_once_with(50, 0)

    def test_get_receipt_returns_receipt(self, service, repo):
        repo.find_by_id.return_value = {"receipt_id": "r1"}
        result = service.get_receipt("r1")
        assert result["receipt_id"] == "r1"

    def test_get_receipt_raises_not_found(self, service, repo):
        repo.find_by_id.return_value = None
        with pytest.raises(NotFoundError):
            service.get_receipt("missing")

    def test_get_receipt_lines(self, service, repo):
        repo.find_lines.return_value = []
        service.get_receipt_lines("r1")
        repo.find_lines.assert_called_once_with("r1")

    def test_create_receipt(self, service, repo):
        receipt_data = {"supplier_id": "sup-1"}
        lines = [{"item_id": "i1", "quantity": 10}]
        service.create_receipt(receipt_data, lines)
        repo.create.assert_called_once_with(receipt_data, lines)

    def test_void_receipt(self, service, repo):
        service.void_receipt("r1", "user-1", "Wrong supplier")
        repo.void_receipt.assert_called_once_with("r1", "user-1", "Wrong supplier")


# ---------------------------------------------------------------------------
# CategoryService
# ---------------------------------------------------------------------------

class TestCategoryService:
    @pytest.fixture
    def service(self):
        return CategoryService(MagicMock())

    def test_list_categories(self, service):
        service.repo.find_all.return_value = {"data": [], "total": 0}
        service.list_categories(50, 0)
        service.repo.find_all.assert_called_once()

    def test_create_category(self, service):
        service.repo.create.return_value = {"category_id": "c1", "name": "Tools"}
        result = service.create_category({"name": "Tools"})
        service.repo.create.assert_called_once_with({"name": "Tools"})

    def test_delete_category(self, service):
        service.delete_category("c1")
        service.repo.remove.assert_called_once_with("c1")


# ---------------------------------------------------------------------------
# LocationService
# ---------------------------------------------------------------------------

class TestLocationService:
    @pytest.fixture
    def service(self):
        return LocationService(MagicMock())

    def test_list_locations(self, service):
        service.repo.find_all.return_value = {"data": [], "total": 0}
        service.list_locations(50, 0)
        service.repo.find_all.assert_called_once()

    def test_create_location(self, service):
        service.create_location({"location_code": "WH-A1"})
        service.repo.create.assert_called_once()

    def test_delete_location(self, service):
        service.delete_location("l1")
        service.repo.remove.assert_called_once_with("l1")


# ---------------------------------------------------------------------------
# SupplierService
# ---------------------------------------------------------------------------

class TestSupplierService:
    @pytest.fixture
    def service(self):
        return SupplierService(MagicMock())

    def test_list_suppliers(self, service):
        service.repo.find_all.return_value = {"data": [], "total": 0}
        service.list_suppliers(50, 0)
        service.repo.find_all.assert_called_once()

    def test_create_supplier(self, service):
        service.create_supplier({"supplier_name": "Acme"})
        service.repo.create.assert_called_once()

    def test_delete_supplier(self, service):
        service.delete_supplier("s1")
        service.repo.remove.assert_called_once_with("s1")


# ---------------------------------------------------------------------------
# CustomerService
# ---------------------------------------------------------------------------

class TestCustomerService:
    @pytest.fixture
    def service(self):
        return CustomerService(MagicMock())

    def test_list_customers(self, service):
        service.repo.find_all.return_value = {"data": [], "total": 0}
        service.list_customers(50, 0)
        service.repo.find_all.assert_called_once()

    def test_create_customer(self, service):
        service.create_customer({"name": "Client A"})
        service.repo.create.assert_called_once()


# ---------------------------------------------------------------------------
# ChannelService
# ---------------------------------------------------------------------------

class TestChannelService:
    @pytest.fixture
    def service(self):
        return ChannelService(MagicMock())

    def test_list_channels(self, service):
        service.repo.find_all.return_value = {"data": [], "total": 0}
        service.list_channels(50, 0)
        service.repo.find_all.assert_called_once()


# ---------------------------------------------------------------------------
# InventoryService
# ---------------------------------------------------------------------------

class TestInventoryService:
    @pytest.fixture
    def service(self):
        return InventoryService(MagicMock())

    def test_list_movements(self, service):
        service.repo.find_all.return_value = {"data": [], "total": 0}
        service.list_movements(50, 0)
        service.repo.find_all.assert_called_once()

    def test_list_on_hand(self, service):
        service.repo.find_on_hand.return_value = []
        service.list_on_hand()
        service.repo.find_on_hand.assert_called_once()


# ---------------------------------------------------------------------------
# SupplierQuoteService
# ---------------------------------------------------------------------------

class TestSupplierQuoteService:
    @pytest.fixture
    def service(self):
        return SupplierQuoteService(MagicMock())

    def test_create_quote(self, service):
        data = {"item_id": "i1", "supplier_id": "s1", "unit_cost": 10, "currency": "USD"}
        service.create_quote(data)
        service.repo.create.assert_called_once_with(data)

    def test_delete_quote(self, service):
        service.delete_quote("q1")
        service.repo.remove.assert_called_once_with("q1")
