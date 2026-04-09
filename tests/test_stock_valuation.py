from unittest.mock import MagicMock, patch

from app.repositories.inventory import InventoryRepository


def _mock_execute(data):
    resp = MagicMock()
    resp.data = data
    return resp


def _chain(*_args, **_kwargs):
    """Return a MagicMock whose further chained calls all return itself."""
    m = MagicMock()
    m.select.return_value = m
    m.order.return_value = m
    m.range.return_value = m
    m.in_.return_value = m
    return m


def _table_router(item_rows, stock_rows, receipt_rows):
    """Return a side_effect callable that routes supabase.table() to the
    right mock chain per table name."""
    item_chain = _chain()
    item_chain.execute.return_value = _mock_execute(item_rows)

    stock_chain = _chain()
    stock_chain.execute.return_value = _mock_execute(stock_rows)

    receipt_chain = _chain()
    receipt_chain.execute.return_value = _mock_execute(receipt_rows)

    def _pick(table_name):
        if table_name == "item":
            return item_chain
        if table_name == "stock":
            return stock_chain
        return receipt_chain

    return _pick


@patch("app.repositories.inventory.supabase")
class TestStockValuation:
    def test_empty_items_returns_empty(self, mock_sb):
        mock_sb.table.side_effect = _table_router([], [], [])

        repo = InventoryRepository()
        assert repo.stock_valuation() == []

    def test_items_with_receipts(self, mock_sb):
        item_rows = [
            {"id": 10, "item_id": "P-100", "description": "Widget"},
            {"id": 20, "item_id": "P-200", "description": "Gadget"},
        ]
        stock_rows = [
            {"id": 1, "item_id": 10, "quantity": 5},
            {"id": 2, "item_id": 10, "quantity": 3},
            {"id": 3, "item_id": 20, "quantity": 7},
        ]
        receipt_rows = [
            {"stock_id": 1, "unit_price": 12.50, "receipt": {"dateTime": "2026-01-01T00:00:00", "status": "ACTIVE"}},
            {"stock_id": 3, "unit_price": 8.00, "receipt": {"dateTime": "2026-02-01T00:00:00", "status": "ACTIVE"}},
        ]

        mock_sb.table.side_effect = _table_router(item_rows, stock_rows, receipt_rows)

        result = InventoryRepository().stock_valuation()

        assert len(result) == 2
        by_id = {r["item_id"]: r for r in result}

        assert by_id["P-100"]["total_quantity"] == 8
        assert by_id["P-100"]["unit_price"] == 12.50
        assert by_id["P-100"]["stock_valuation"] == 100.0

        assert by_id["P-200"]["total_quantity"] == 7
        assert by_id["P-200"]["unit_price"] == 8.00
        assert by_id["P-200"]["stock_valuation"] == 56.0

    def test_voided_receipts_skipped(self, mock_sb):
        item_rows = [{"id": 10, "item_id": "P-100", "description": "Widget"}]
        stock_rows = [{"id": 1, "item_id": 10, "quantity": 4}]
        receipt_rows = [
            {"stock_id": 1, "unit_price": 99.0, "receipt": {"dateTime": "2026-03-01T00:00:00", "status": "VOIDED"}},
            {"stock_id": 1, "unit_price": 10.0, "receipt": {"dateTime": "2026-01-01T00:00:00", "status": "ACTIVE"}},
        ]

        mock_sb.table.side_effect = _table_router(item_rows, stock_rows, receipt_rows)

        result = InventoryRepository().stock_valuation()
        assert result[0]["unit_price"] == 10.0
        assert result[0]["stock_valuation"] == 40.0

    def test_no_receipts_gives_null_price(self, mock_sb):
        item_rows = [{"id": 10, "item_id": "P-100", "description": "Widget"}]
        stock_rows = [{"id": 1, "item_id": 10, "quantity": 3}]

        mock_sb.table.side_effect = _table_router(item_rows, stock_rows, [])

        result = InventoryRepository().stock_valuation()
        assert result[0]["unit_price"] is None
        assert result[0]["stock_valuation"] is None

    def test_latest_receipt_wins(self, mock_sb):
        item_rows = [{"id": 10, "item_id": "P-100", "description": "W"}]
        stock_rows = [{"id": 1, "item_id": 10, "quantity": 2}]
        receipt_rows = [
            {"stock_id": 1, "unit_price": 5.0, "receipt": {"dateTime": "2026-01-01T00:00:00", "status": "ACTIVE"}},
            {"stock_id": 1, "unit_price": 15.0, "receipt": {"dateTime": "2026-06-01T00:00:00", "status": "ACTIVE"}},
        ]

        mock_sb.table.side_effect = _table_router(item_rows, stock_rows, receipt_rows)

        result = InventoryRepository().stock_valuation()
        assert result[0]["unit_price"] == 15.0
        assert result[0]["stock_valuation"] == 30.0

    def test_items_without_stock_included(self, mock_sb):
        """Items that exist in the catalogue but have no stock rows should
        still appear with total_quantity=0 and null valuation."""
        item_rows = [
            {"id": 10, "item_id": "P-100", "description": "Widget"},
            {"id": 20, "item_id": "P-200", "description": "Gadget"},
            {"id": 30, "item_id": "P-300", "description": "Sprocket"},
        ]
        stock_rows = [
            {"id": 1, "item_id": 10, "quantity": 5},
        ]
        receipt_rows = [
            {"stock_id": 1, "unit_price": 10.0, "receipt": {"dateTime": "2026-01-01T00:00:00", "status": "ACTIVE"}},
        ]

        mock_sb.table.side_effect = _table_router(item_rows, stock_rows, receipt_rows)

        result = InventoryRepository().stock_valuation()

        assert len(result) == 3
        by_id = {r["item_id"]: r for r in result}

        assert by_id["P-100"]["total_quantity"] == 5
        assert by_id["P-100"]["unit_price"] == 10.0
        assert by_id["P-100"]["stock_valuation"] == 50.0

        assert by_id["P-200"]["total_quantity"] == 0
        assert by_id["P-200"]["unit_price"] is None
        assert by_id["P-200"]["stock_valuation"] is None

        assert by_id["P-300"]["total_quantity"] == 0
        assert by_id["P-300"]["unit_price"] is None
        assert by_id["P-300"]["stock_valuation"] is None
