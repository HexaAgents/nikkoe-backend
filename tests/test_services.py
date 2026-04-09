"""Tests for the service layer using mocked repositories.

Services contain the business logic of the application. By mocking the
repositories, we test that logic in isolation — no database, no network,
just pure Python. This makes tests fast and deterministic.
"""

import re
from unittest.mock import MagicMock

import pytest

from app.errors import NotFoundError
from app.repositories.base import dash_insensitive_pattern
from app.services.category import CategoryService
from app.services.channel import ChannelService
from app.services.currency import CurrencyService
from app.services.customer import CustomerService
from app.services.inventory import InventoryService
from app.services.item import ItemService
from app.services.location import LocationService
from app.services.receipt import ReceiptService
from app.services.sale import SaleService
from app.services.supplier import SupplierService
from app.services.supplier_quote import SupplierQuoteService
from app.services.user import UserService

# ---------------------------------------------------------------------------
# dash_insensitive_pattern (pure function from base.py)
# ---------------------------------------------------------------------------


class TestDashInsensitivePattern:
    def test_basic_query_produces_regex(self):
        pattern = dash_insensitive_pattern("abc")
        assert re.fullmatch(pattern, "abc")
        assert re.fullmatch(pattern, "a-b-c")
        assert re.fullmatch(pattern, "xabc")
        assert re.fullmatch(pattern, "abcx")

    def test_query_with_dashes_strips_them(self):
        pattern = dash_insensitive_pattern("2sd-823")
        assert re.fullmatch(pattern, "2sd823")
        assert re.fullmatch(pattern, "2sd-823")
        assert re.fullmatch(pattern, "2-s-d-8-2-3")

    def test_empty_after_strip_returns_wildcard(self):
        pattern = dash_insensitive_pattern("---")
        assert pattern == ".*"

    def test_empty_string_returns_wildcard(self):
        pattern = dash_insensitive_pattern("")
        assert pattern == ".*"

    def test_special_regex_chars_are_escaped(self):
        pattern = dash_insensitive_pattern("a.b")
        assert re.fullmatch(pattern, "a.b")
        assert not re.fullmatch(pattern, "axb")


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
        repos["repo"].find_all.assert_called_once_with(10, 0, sort_by="item_id")
        assert result == {"data": [], "total": 0}

    def test_list_items_uses_defaults(self, service, repos):
        repos["repo"].find_all.return_value = {"data": [], "total": 0}
        service.list_items()
        repos["repo"].find_all.assert_called_once_with(50, 0, sort_by="item_id")

    def test_get_item_returns_item_when_found(self, service, repos):
        repos["repo"].find_by_id.return_value = {"item_id": "1", "part_number": "X"}
        result = service.get_item("1")
        assert result["part_number"] == "X"

    def test_get_item_raises_not_found(self, service, repos):
        repos["repo"].find_by_id.return_value = None
        with pytest.raises(NotFoundError) as exc_info:
            service.get_item(999)
        assert exc_info.value.status_code == 404
        assert "999" in exc_info.value.message

    def test_create_item_delegates_to_repo(self, service, repos):
        data = {"part_number": "NEW-1"}
        repos["repo"].create.return_value = {"item_id": "2", **data}
        result = service.create_item(data)
        repos["repo"].create.assert_called_once_with(data)
        assert result["part_number"] == "NEW-1"

    def test_update_item_delegates_to_repo(self, service, repos):
        repos["repo"].update.return_value = {"item_id": "1", "description": "Updated"}
        service.update_item("1", {"description": "Updated"})
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
        service.get_item_inventory("1")
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
        service.list_sales(25, 10)
        repo.find_all.assert_called_once_with(25, 10, status=None)

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
        service.get_sale_lines("s1")
        repo.find_lines.assert_called_once_with("s1")

    def test_create_sale(self, service, repo):
        sale_data = {"customer_name": "Test"}
        lines = [{"item_id": "i1", "quantity": 2}]
        repo.create.return_value = {"sale_id": "s1"}
        service.create_sale(sale_data, lines)
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
        repo.find_all.assert_called_once_with(50, 0, status=None)

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
        svc = CategoryService(MagicMock(), item_repo=MagicMock())
        return svc

    def test_list_categories(self, service):
        service.repo.find_all.return_value = {"data": [], "total": 0}
        service.list_categories(50, 0)
        service.repo.find_all.assert_called_once()

    def test_list_categories_passes_search(self, service):
        service.repo.find_all.return_value = {"data": [], "total": 0}
        service.list_categories(50, 0, search="Tools")
        service.repo.find_all.assert_called_once_with(50, 0, search="Tools")

    def test_get_category_returns_category(self, service):
        service.repo.find_by_id.return_value = {"id": 1, "name": "Tools"}
        result = service.get_category(1)
        assert result["name"] == "Tools"
        service.repo.find_by_id.assert_called_once_with(1)

    def test_get_category_raises_not_found(self, service):
        service.repo.find_by_id.return_value = None
        with pytest.raises(NotFoundError):
            service.get_category(999)

    def test_get_category_items(self, service):
        service.repo.find_by_id.return_value = {"id": 1, "name": "Tools"}
        service.item_repo.find_by_category.return_value = {"data": [], "total": 0}
        service.get_category_items(1, 50, 0)
        service.item_repo.find_by_category.assert_called_once_with(1, 50, 0)

    def test_create_category(self, service):
        service.repo.create.return_value = {"category_id": "c1", "name": "Tools"}
        service.create_category({"name": "Tools"})
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

    def test_list_locations_passes_search(self, service):
        service.repo.find_all.return_value = {"data": [], "total": 0}
        service.list_locations(50, 0, search="WH")
        service.repo.find_all.assert_called_once_with(50, 0, search="WH")

    def test_get_location_items_returns_items(self, service):
        service.repo.find_by_id.return_value = {"id": 1, "code": "WH-A"}
        service.repo.find_items_by_location.return_value = []
        result = service.get_location_items(1)
        service.repo.find_items_by_location.assert_called_once_with(1)
        assert result == []

    def test_get_location_items_raises_not_found(self, service):
        service.repo.find_by_id.return_value = None
        with pytest.raises(NotFoundError):
            service.get_location_items(999)

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
        return SupplierService(MagicMock(), receipt_repo=MagicMock())

    def test_list_suppliers(self, service):
        service.repo.find_all.return_value = {"data": [], "total": 0}
        service.list_suppliers(50, 0)
        service.repo.find_all.assert_called_once()

    def test_list_suppliers_passes_search(self, service):
        service.repo.find_all.return_value = {"data": [], "total": 0}
        service.list_suppliers(50, 0, search="Acme")
        service.repo.find_all.assert_called_once_with(50, 0, search="Acme")

    def test_get_supplier(self, service):
        service.repo.find_by_id.return_value = {"id": 1, "name": "Acme"}
        result = service.get_supplier(1)
        assert result["name"] == "Acme"

    def test_get_supplier_receipts(self, service):
        service.receipt_repo.find_by_supplier_id.return_value = []
        result = service.get_supplier_receipts(1)
        service.receipt_repo.find_by_supplier_id.assert_called_once_with(1)
        assert result == []

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
        service.repo.find_movements.return_value = {"data": [], "total": 0}
        service.list_movements(50, 0)
        service.repo.find_movements.assert_called_once()

    def test_list_movements_passes_search(self, service):
        service.repo.find_movements.return_value = {"data": [], "total": 0}
        service.list_movements(50, 0, search="transfer")
        service.repo.find_movements.assert_called_once_with(50, 0, search="transfer")

    def test_list_on_hand(self, service):
        service.repo.find_on_hand.return_value = []
        service.list_on_hand()
        service.repo.find_on_hand.assert_called_once()

    def test_stock_valuation(self, service):
        service.repo.stock_valuation.return_value = [
            {"item_id": "P1", "description": "Part 1", "total_quantity": 10, "unit_price": 5.0, "stock_valuation": 50.0}
        ]
        result = service.stock_valuation()
        service.repo.stock_valuation.assert_called_once()
        assert len(result) == 1


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


# ---------------------------------------------------------------------------
# SaleService — search branch
# ---------------------------------------------------------------------------


class TestSaleServiceSearch:
    @pytest.fixture
    def repo(self):
        return MagicMock()

    @pytest.fixture
    def service(self, repo):
        return SaleService(repo)

    def test_list_sales_with_search_delegates_to_search(self, service, repo):
        repo.search_by_part_number.return_value = {"data": [], "total": 0}
        service.list_sales(50, 0, search="PART-1")
        repo.search_by_part_number.assert_called_once_with("PART-1", limit=50, offset=0, status=None)
        repo.find_all.assert_not_called()

    def test_list_sales_without_search_delegates_to_find_all(self, service, repo):
        repo.find_all.return_value = {"data": [], "total": 0}
        service.list_sales(25, 10)
        repo.find_all.assert_called_once_with(25, 10, status=None)
        repo.search_by_part_number.assert_not_called()

    def test_list_sales_none_search_delegates_to_find_all(self, service, repo):
        repo.find_all.return_value = {"data": [], "total": 0}
        service.list_sales(50, 0, search=None)
        repo.find_all.assert_called_once_with(50, 0, status=None)


# ---------------------------------------------------------------------------
# ReceiptService — search branch
# ---------------------------------------------------------------------------


class TestReceiptServiceSearch:
    @pytest.fixture
    def repo(self):
        return MagicMock()

    @pytest.fixture
    def service(self, repo):
        return ReceiptService(repo)

    def test_list_receipts_with_search_delegates_to_search(self, service, repo):
        repo.search_by_part_number.return_value = {"data": [], "total": 0}
        service.list_receipts(50, 0, search="PART-2")
        repo.search_by_part_number.assert_called_once_with("PART-2", limit=50, offset=0, status=None)
        repo.find_all.assert_not_called()

    def test_list_receipts_without_search_delegates_to_find_all(self, service, repo):
        repo.find_all.return_value = {"data": [], "total": 0}
        service.list_receipts(25, 10)
        repo.find_all.assert_called_once_with(25, 10, status=None)


# ---------------------------------------------------------------------------
# ItemService — search
# ---------------------------------------------------------------------------


class TestItemServiceSearch:
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

    def test_search_items_delegates_to_repo(self, service, repos):
        repos["repo"].search.return_value = {"data": [], "total": 0}
        service.search_items("PART", 100, 0, in_stock=False)
        repos["repo"].search.assert_called_once_with("PART", 100, 0, in_stock=False, sort_by="item_id")

    def test_search_items_with_in_stock(self, service, repos):
        repos["repo"].search.return_value = {"data": [], "total": 0}
        service.search_items("X", 50, 0, in_stock=True)
        repos["repo"].search.assert_called_once_with("X", 50, 0, in_stock=True, sort_by="item_id")


# ---------------------------------------------------------------------------
# InventoryService — transfer
# ---------------------------------------------------------------------------


class TestInventoryServiceTransfer:
    @pytest.fixture
    def service(self):
        return InventoryService(MagicMock())

    def test_transfer_stock_delegates_to_repo(self, service):
        service.repo.create_transfer.return_value = {"transfer_id": 1}
        result = service.transfer_stock(from_stock_id=10, to_location_id=20, quantity=5, user_id=1, notes="test")
        service.repo.create_transfer.assert_called_once_with(10, 20, 5, 1, "test")
        assert result["transfer_id"] == 1

    def test_transfer_stock_without_user_or_notes(self, service):
        service.repo.create_transfer.return_value = {"transfer_id": 2}
        service.transfer_stock(from_stock_id=1, to_location_id=2, quantity=1)
        service.repo.create_transfer.assert_called_once_with(1, 2, 1, None, None)


# ---------------------------------------------------------------------------
# CurrencyService
# ---------------------------------------------------------------------------


class TestCurrencyService:
    @pytest.fixture
    def service(self):
        return CurrencyService(MagicMock())

    def test_list_currencies(self, service):
        service.repo.find_all.return_value = {"data": [{"id": 1, "code": "GBP"}], "total": 1}
        result = service.list_currencies(50, 0)
        service.repo.find_all.assert_called_once_with(50, 0)
        assert result["total"] == 1

    def test_list_currencies_uses_defaults(self, service):
        service.repo.find_all.return_value = {"data": [], "total": 0}
        service.list_currencies()
        service.repo.find_all.assert_called_once_with(50, 0)


# ---------------------------------------------------------------------------
# UserService
# ---------------------------------------------------------------------------


class TestUserService:
    @pytest.fixture
    def service(self):
        return UserService(MagicMock())

    def test_get_profile_returns_profile_when_present(self, service):
        from app.middleware.auth import UserProfile

        profile = UserProfile(user_id=1, first_name="A", last_name="B", email="a@b.com")
        result = service.get_profile(profile)
        assert result.user_id == 1

    def test_get_profile_raises_not_found_when_none(self, service):
        with pytest.raises(NotFoundError) as exc_info:
            service.get_profile(None)
        assert exc_info.value.status_code == 404

    def test_create_user_delegates_to_repo(self, service):
        service.repo.create_auth_user.return_value = {"id": "uid", "email": "new@b.com"}
        result = service.create_user("new@b.com", "pass123")
        service.repo.create_auth_user.assert_called_once_with("new@b.com", "pass123")
        assert result["email"] == "new@b.com"
