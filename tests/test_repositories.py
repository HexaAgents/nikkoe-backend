"""Repository-level unit tests.

These tests mock the Supabase client at the import boundary
(``app.repositories.<module>.supabase``) and verify the query-building
and branching logic that lives inside each repository class.
"""

import inspect
from unittest.mock import MagicMock, patch

import pytest

from app.errors import AppError
from app.repositories.base import _is_transient, retry_transient
from app.repositories.inventory import InventoryRepository
from app.repositories.location import LocationRepository
from app.repositories.supplier_quote import SupplierQuoteRepository

# =====================================================================
# SupplierQuoteRepository.create — upsert logic
# =====================================================================


class TestSupplierQuoteRepositoryCreate:
    DATA = {"item_id": 1, "supplier_id": 2, "cost": 10.0, "currency_id": 1}

    @patch("app.repositories.supplier_quote.supabase")
    def test_create_upserts_and_returns_row(self, mock_sb):
        table = mock_sb.table.return_value
        table.upsert.return_value.execute.return_value = MagicMock(data=[{"id": 99, **self.DATA}])

        repo = SupplierQuoteRepository()
        result = repo.create(dict(self.DATA))

        table.upsert.assert_called_once_with(self.DATA, on_conflict="item_id,supplier_id")
        assert result["id"] == 99

    @patch("app.repositories.supplier_quote.supabase")
    def test_create_updates_existing_via_upsert(self, mock_sb):
        """Upsert with matching item_id+supplier_id updates the existing row."""
        table = mock_sb.table.return_value
        table.upsert.return_value.execute.return_value = MagicMock(data=[{"id": 42, "cost": 10.0, "currency_id": 1}])

        repo = SupplierQuoteRepository()
        result = repo.create(dict(self.DATA))

        assert result["id"] == 42

    @patch("app.repositories.supplier_quote.supabase")
    def test_create_wraps_unexpected_errors_in_app_error(self, mock_sb):
        table = mock_sb.table.return_value
        table.upsert.return_value.execute.side_effect = RuntimeError("connection lost")

        repo = SupplierQuoteRepository()
        with pytest.raises(AppError) as exc_info:
            repo.create(dict(self.DATA))

        assert exc_info.value.status_code == 400
        assert "Failed to save supplier quote" in exc_info.value.message

    def test_create_does_not_use_maybe_single(self):
        """Guard: the method must never use .maybe_single()."""
        source = inspect.getsource(SupplierQuoteRepository.create)
        assert "maybe_single" not in source


# =====================================================================
# SupplierQuoteRepository.find_by_item_id
# =====================================================================


class TestSupplierQuoteRepositoryFindByItemId:
    @patch("app.repositories.supplier_quote.supabase")
    def test_returns_rows(self, mock_sb):
        rows = [{"id": 1}, {"id": 2}]
        (
            mock_sb.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value
        ) = MagicMock(data=rows)

        result = SupplierQuoteRepository().find_by_item_id(1)
        assert result == rows

    @patch("app.repositories.supplier_quote.supabase")
    def test_returns_empty_list_when_none(self, mock_sb):
        (
            mock_sb.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value
        ) = MagicMock(data=None)

        result = SupplierQuoteRepository().find_by_item_id(1)
        assert result == []


# =====================================================================
# SupplierQuoteRepository.remove
# =====================================================================


class TestSupplierQuoteRepositoryRemove:
    @patch("app.repositories.supplier_quote.supabase")
    def test_remove_calls_delete(self, mock_sb):
        SupplierQuoteRepository().remove(5)
        mock_sb.table.return_value.delete.return_value.eq.assert_called_once_with("id", 5)


# =====================================================================
# InventoryRepository.find_on_hand
# =====================================================================


class TestInventoryRepositoryFindOnHand:
    @patch("app.repositories.inventory.supabase")
    def test_returns_all_rows(self, mock_sb):
        rows = [{"id": 1, "quantity": 5}, {"id": 2, "quantity": 10}]
        (
            mock_sb.table.return_value.select.return_value.order.return_value.range.return_value.execute.return_value
        ) = MagicMock(data=rows)

        result = InventoryRepository().find_on_hand()
        assert result == rows

    @patch("app.repositories.inventory.supabase")
    def test_returns_empty_list_when_no_stock(self, mock_sb):
        (
            mock_sb.table.return_value.select.return_value.order.return_value.range.return_value.execute.return_value
        ) = MagicMock(data=[])

        result = InventoryRepository().find_on_hand()
        assert result == []

    @patch("app.repositories.inventory.supabase")
    def test_retries_transient_errors(self, mock_sb):
        chain = mock_sb.table.return_value.select.return_value.order.return_value.range.return_value
        chain.execute.side_effect = [
            Exception("<ConnectionTerminated error_code:1>"),
            MagicMock(data=[{"id": 1}]),
        ]

        result = InventoryRepository().find_on_hand()
        assert result == [{"id": 1}]
        assert chain.execute.call_count == 2

    @patch("app.repositories.inventory.supabase")
    def test_raises_after_retries_exhausted(self, mock_sb):
        mock_sb.table.return_value.select.return_value.order.return_value.range.return_value.execute.side_effect = (
            Exception("<ConnectionTerminated error_code:1>")
        )

        with pytest.raises(Exception, match="ConnectionTerminated"):
            InventoryRepository().find_on_hand()


# =====================================================================
# InventoryRepository.create_cross_transfer — maybe_single guard
# =====================================================================


class TestInventoryRepositoryCrossTransfer:
    def test_create_cross_transfer_does_not_use_maybe_single(self):
        """Guard: must use .limit(1) not .maybe_single() on stock lookups."""
        source = inspect.getsource(InventoryRepository.create_cross_transfer)
        assert "maybe_single" not in source


# =====================================================================
# LocationRepository.find_all — stock summary chunking
# =====================================================================


class TestLocationRepositoryFindAll:
    @patch("app.repositories.location.supabase")
    def test_find_all_returns_locations_with_stock_summary(self, mock_sb):
        table = mock_sb.table.return_value
        loc_rows = [{"id": 1, "code": "WH-A"}, {"id": 2, "code": "WH-B"}]
        stock_rows = [
            {"location_id": 1, "item_id": 10, "quantity": 5},
            {"location_id": 1, "item_id": 11, "quantity": 3},
        ]

        loc_response = MagicMock(data=loc_rows, count=2)
        stock_response = MagicMock(data=stock_rows)
        empty_stock = MagicMock(data=[])

        call_count = {"n": 0}

        def select_side_effect(*args, **kwargs):
            call_count["n"] += 1
            mock_chain = MagicMock()
            if call_count["n"] == 1:
                mock_chain.order.return_value.range.return_value.execute.return_value = loc_response
            elif call_count["n"] == 2:
                mock_chain.in_.return_value.gt.return_value.range.return_value.execute.return_value = stock_response
            else:
                mock_chain.in_.return_value.gt.return_value.range.return_value.execute.return_value = empty_stock
            return mock_chain

        table.select.side_effect = select_side_effect

        repo = LocationRepository()
        result = repo.find_all(limit=100, offset=0)

        assert result["total"] == 2
        assert len(result["data"]) == 2
        wh_a = result["data"][0]
        assert wh_a["total_quantity"] == 8
        assert wh_a["part_count"] == 2
        wh_b = result["data"][1]
        assert wh_b["total_quantity"] == 0
        assert wh_b["part_count"] == 0

    @patch("app.repositories.location.supabase")
    def test_get_stock_summary_chunks_large_location_lists(self, mock_sb):
        """Regression: .in_() must be chunked so the URL doesn't exceed PostgREST limits."""
        table = mock_sb.table.return_value

        location_ids = list(range(1, 602))

        call_count = {"n": 0}

        def select_side_effect(*args, **kwargs):
            call_count["n"] += 1
            mock_chain = MagicMock()
            mock_chain.in_.return_value.gt.return_value.range.return_value.execute.return_value = MagicMock(data=[])
            return mock_chain

        table.select.side_effect = select_side_effect

        repo = LocationRepository()
        result = repo._get_stock_summary(location_ids)

        assert call_count["n"] >= 3, f"Expected at least 3 chunked .in_() calls for 601 IDs, got {call_count['n']}"
        assert result == {}

    def test_get_stock_summary_empty_ids_returns_empty(self):
        repo = LocationRepository()
        assert repo._get_stock_summary([]) == {}


# =====================================================================
# retry_transient — decorator for HTTP/2 GOAWAY / socket exhaustion
# =====================================================================


class TestRetryTransient:
    def test_returns_value_on_success(self):
        @retry_transient(max_retries=2, backoff=0)
        def ok():
            return 42

        assert ok() == 42

    def test_retries_on_connection_terminated(self):
        calls = {"n": 0}

        @retry_transient(max_retries=2, backoff=0)
        def flaky():
            calls["n"] += 1
            if calls["n"] == 1:
                raise Exception("<ConnectionTerminated error_code:1, last_stream_id:39>")
            return "ok"

        assert flaky() == "ok"
        assert calls["n"] == 2

    def test_retries_on_errno_35(self):
        calls = {"n": 0}

        @retry_transient(max_retries=2, backoff=0)
        def flaky():
            calls["n"] += 1
            if calls["n"] == 1:
                raise OSError("[Errno 35] Resource temporarily unavailable")
            return "ok"

        assert flaky() == "ok"
        assert calls["n"] == 2

    def test_raises_after_max_retries_exhausted(self):
        @retry_transient(max_retries=2, backoff=0)
        def always_fails():
            raise Exception("<ConnectionTerminated error_code:1>")

        with pytest.raises(Exception, match="ConnectionTerminated"):
            always_fails()

    def test_does_not_retry_non_transient_errors(self):
        calls = {"n": 0}

        @retry_transient(max_retries=2, backoff=0)
        def real_bug():
            calls["n"] += 1
            raise ValueError("actual programming error")

        with pytest.raises(ValueError, match="actual programming error"):
            real_bug()

        assert calls["n"] == 1, "Should not retry non-transient errors"


class TestIsTransient:
    @pytest.mark.parametrize(
        "msg",
        [
            "<ConnectionTerminated error_code:1, last_stream_id:39, additional_data:None>",
            "[Errno 35] Resource temporarily unavailable",
            "[Errno 54] Connection reset by peer",
            "Server disconnected without sending a response",
            "RemoteProtocolError: peer closed connection",
        ],
    )
    def test_detects_transient_errors(self, msg):
        assert _is_transient(Exception(msg)) is True

    @pytest.mark.parametrize(
        "msg",
        [
            "duplicate key value violates unique constraint",
            "column 'x' does not exist",
            "invalid input syntax",
        ],
    )
    def test_rejects_non_transient_errors(self, msg):
        assert _is_transient(Exception(msg)) is False


class TestRepositoriesUseRetryDecorator:
    """Guard: key repository methods must be decorated with retry_transient."""

    @pytest.mark.parametrize(
        "repo_cls,method_name",
        [
            (InventoryRepository, "find_movements"),
            (InventoryRepository, "find_on_hand"),
            (InventoryRepository, "find_by_item_id"),
            (InventoryRepository, "stock_valuation"),
            (LocationRepository, "find_all"),
            (LocationRepository, "find_by_id"),
            (SupplierQuoteRepository, "find_by_item_id"),
        ],
    )
    def test_method_is_retry_wrapped(self, repo_cls, method_name):
        method = getattr(repo_cls, method_name)
        assert hasattr(method, "__wrapped__"), (
            f"{repo_cls.__name__}.{method_name} must be decorated with @retry_transient"
        )
