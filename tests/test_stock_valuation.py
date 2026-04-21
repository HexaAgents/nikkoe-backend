from unittest.mock import MagicMock, patch

from app.repositories.inventory import InventoryRepository


@patch("app.repositories.inventory.supabase")
class TestStockValuation:
    def test_empty_view_returns_empty(self, mock_sb):
        mock_sb.table.return_value.select.return_value.order.return_value.range.return_value.execute.return_value = (
            MagicMock(data=[])
        )

        repo = InventoryRepository()
        assert repo.stock_valuation() == []
        mock_sb.table.assert_called_with("v_stock_valuation")

    def test_returns_rows_from_view(self, mock_sb):
        view_rows = [
            {
                "id": 10,
                "item_id": "P-100",
                "description": "Widget",
                "total_quantity": 8,
                "unit_price": 12.50,
                "stock_valuation": 100.0,
            },
            {
                "id": 20,
                "item_id": "P-200",
                "description": "Gadget",
                "total_quantity": 7,
                "unit_price": 8.00,
                "stock_valuation": 56.0,
            },
        ]
        mock_sb.table.return_value.select.return_value.order.return_value.range.return_value.execute.return_value = (
            MagicMock(data=view_rows)
        )

        result = InventoryRepository().stock_valuation()

        assert len(result) == 2
        assert result[0]["item_id"] == "P-100"
        assert result[0]["stock_valuation"] == 100.0
        assert result[1]["item_id"] == "P-200"

    def test_null_price_items_included(self, mock_sb):
        view_rows = [
            {
                "id": 10,
                "item_id": "P-100",
                "description": "Widget",
                "total_quantity": 0,
                "unit_price": None,
                "stock_valuation": None,
            },
        ]
        mock_sb.table.return_value.select.return_value.order.return_value.range.return_value.execute.return_value = (
            MagicMock(data=view_rows)
        )

        result = InventoryRepository().stock_valuation()
        assert result[0]["unit_price"] is None
        assert result[0]["stock_valuation"] is None

    def test_paginates_large_results(self, mock_sb):
        """View results paginate through 1000-row pages."""
        page1 = [
            {
                "id": i,
                "item_id": f"P-{i}",
                "description": "X",
                "total_quantity": 1,
                "unit_price": 1.0,
                "stock_valuation": 1.0,
            }
            for i in range(1000)
        ]
        page2 = [
            {
                "id": 1000,
                "item_id": "P-1000",
                "description": "Y",
                "total_quantity": 2,
                "unit_price": 2.0,
                "stock_valuation": 4.0,
            }
        ]

        call_count = {"n": 0}

        def range_side_effect(*args, **kwargs):
            call_count["n"] += 1
            m = MagicMock()
            m.execute.return_value = MagicMock(data=page1 if call_count["n"] == 1 else page2)
            return m

        mock_sb.table.return_value.select.return_value.order.return_value.range.side_effect = range_side_effect

        result = InventoryRepository().stock_valuation()
        assert len(result) == 1001
        assert call_count["n"] == 2
