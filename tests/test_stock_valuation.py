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


@patch("app.repositories.inventory.supabase")
class TestStockValuation:
    def test_empty_stock_returns_empty(self, mock_sb):
        chain = _chain()
        chain.execute.return_value = _mock_execute([])
        mock_sb.table.return_value = chain

        repo = InventoryRepository()
        assert repo.stock_valuation() == []

    def test_items_with_receipts(self, mock_sb):
        stock_rows = [
            {"id": 1, "item_id": 10, "quantity": 5, "item": {"id": 10, "item_id": "P-100", "description": "Widget"}},
            {"id": 2, "item_id": 10, "quantity": 3, "item": {"id": 10, "item_id": "P-100", "description": "Widget"}},
            {"id": 3, "item_id": 20, "quantity": 7, "item": {"id": 20, "item_id": "P-200", "description": "Gadget"}},
        ]
        receipt_rows = [
            {"stock_id": 1, "unit_price": 12.50, "receipt": {"dateTime": "2026-01-01T00:00:00", "status": "ACTIVE"}},
            {"stock_id": 3, "unit_price": 8.00, "receipt": {"dateTime": "2026-02-01T00:00:00", "status": "ACTIVE"}},
        ]

        stock_chain = _chain()
        stock_chain.execute.return_value = _mock_execute(stock_rows)

        receipt_chain = _chain()
        receipt_chain.execute.return_value = _mock_execute(receipt_rows)

        mock_sb.table.side_effect = lambda t: stock_chain if t == "stock" else receipt_chain

        repo = InventoryRepository()
        result = repo.stock_valuation()

        assert len(result) == 2
        by_id = {r["item_id"]: r for r in result}

        assert by_id["P-100"]["total_quantity"] == 8
        assert by_id["P-100"]["unit_price"] == 12.50
        assert by_id["P-100"]["stock_valuation"] == 100.0

        assert by_id["P-200"]["total_quantity"] == 7
        assert by_id["P-200"]["unit_price"] == 8.00
        assert by_id["P-200"]["stock_valuation"] == 56.0

    def test_voided_receipts_skipped(self, mock_sb):
        stock_rows = [
            {"id": 1, "item_id": 10, "quantity": 4, "item": {"id": 10, "item_id": "P-100", "description": "Widget"}},
        ]
        receipt_rows = [
            {"stock_id": 1, "unit_price": 99.0, "receipt": {"dateTime": "2026-03-01T00:00:00", "status": "VOIDED"}},
            {"stock_id": 1, "unit_price": 10.0, "receipt": {"dateTime": "2026-01-01T00:00:00", "status": "ACTIVE"}},
        ]

        stock_chain = _chain()
        stock_chain.execute.return_value = _mock_execute(stock_rows)

        receipt_chain = _chain()
        receipt_chain.execute.return_value = _mock_execute(receipt_rows)

        mock_sb.table.side_effect = lambda t: stock_chain if t == "stock" else receipt_chain

        result = InventoryRepository().stock_valuation()
        assert result[0]["unit_price"] == 10.0
        assert result[0]["stock_valuation"] == 40.0

    def test_no_receipts_gives_null_price(self, mock_sb):
        stock_rows = [
            {"id": 1, "item_id": 10, "quantity": 3, "item": {"id": 10, "item_id": "P-100", "description": "Widget"}},
        ]

        stock_chain = _chain()
        stock_chain.execute.return_value = _mock_execute(stock_rows)

        receipt_chain = _chain()
        receipt_chain.execute.return_value = _mock_execute([])

        mock_sb.table.side_effect = lambda t: stock_chain if t == "stock" else receipt_chain

        result = InventoryRepository().stock_valuation()
        assert result[0]["unit_price"] is None
        assert result[0]["stock_valuation"] is None

    def test_latest_receipt_wins(self, mock_sb):
        stock_rows = [
            {"id": 1, "item_id": 10, "quantity": 2, "item": {"id": 10, "item_id": "P-100", "description": "W"}},
        ]
        receipt_rows = [
            {"stock_id": 1, "unit_price": 5.0, "receipt": {"dateTime": "2026-01-01T00:00:00", "status": "ACTIVE"}},
            {"stock_id": 1, "unit_price": 15.0, "receipt": {"dateTime": "2026-06-01T00:00:00", "status": "ACTIVE"}},
        ]

        stock_chain = _chain()
        stock_chain.execute.return_value = _mock_execute(stock_rows)

        receipt_chain = _chain()
        receipt_chain.execute.return_value = _mock_execute(receipt_rows)

        mock_sb.table.side_effect = lambda t: stock_chain if t == "stock" else receipt_chain

        result = InventoryRepository().stock_valuation()
        assert result[0]["unit_price"] == 15.0
        assert result[0]["stock_valuation"] == 30.0
