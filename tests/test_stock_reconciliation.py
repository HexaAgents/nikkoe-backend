from pathlib import Path

from scripts.reconcile_stock_discrepancies import (
    AUTO_OFFSET_PLACEHOLDER,
    MANUAL_INSUFFICIENT_POSITIVE_STOCK,
    MANUAL_NEGATIVE_TOTAL,
    MANUAL_NO_POSITIVE_STOCK,
    MANUAL_REAL_NEGATIVE_LOCATION,
    ItemRow,
    StockRow,
    classify_item,
    write_csv,
)


def item(part_number: str = "TC514400Z-80") -> ItemRow:
    return ItemRow(id=1, item_id=part_number, description="test item")


def stock(stock_id: int, qty: int, code: str, *, location_id: int | None = None) -> StockRow:
    return StockRow(
        id=stock_id,
        item_id=1,
        location_id=location_id or stock_id,
        quantity=qty,
        location_code=code,
    )


class TestStockReconciliationClassification:
    def test_tc514400z_style_placeholder_offset_preserves_total(self):
        result = classify_item(item(), [stock(10, -2, "0"), stock(11, 10, "s1b")])

        assert result is not None
        assert result.classification == AUTO_OFFSET_PLACEHOLDER
        assert result.total == 8
        assert result.positive_total == 10
        assert len(result.adjustments) == 2
        assert sum(adj.quantity_delta for adj in result.adjustments) == 0

        by_location = {adj.location_code: adj for adj in result.adjustments}
        assert by_location["0"].quantity_before == -2
        assert by_location["0"].quantity_delta == 2
        assert by_location["0"].quantity_after == 0
        assert by_location["s1b"].quantity_before == 10
        assert by_location["s1b"].quantity_delta == -2
        assert by_location["s1b"].quantity_after == 8

    def test_allocates_placeholder_debt_across_multiple_positive_locations(self):
        result = classify_item(
            item("MULTI"),
            [
                stock(10, -7, "PegNotIdentified"),
                stock(11, 5, "A"),
                stock(12, 10, "B"),
            ],
        )

        assert result is not None
        assert result.classification == AUTO_OFFSET_PLACEHOLDER
        assert result.total == 8
        assert sum(adj.quantity_delta for adj in result.adjustments) == 0
        by_location = {adj.location_code: adj for adj in result.adjustments}
        assert by_location["PegNotIdentified"].quantity_after == 0
        # Highest-quantity positive location is used first.
        assert by_location["B"].quantity_after == 3
        assert "A" not in by_location

    def test_manual_when_net_total_is_negative(self):
        result = classify_item(item("NEG"), [stock(10, -3, "0"), stock(11, 1, "A")])

        assert result is not None
        assert result.classification == MANUAL_NEGATIVE_TOTAL
        assert result.adjustments == []

    def test_manual_when_no_positive_real_stock_exists(self):
        result = classify_item(item("NO-POS"), [stock(10, -1, "0"), stock(11, 3, "PegNotIdentified")])

        assert result is not None
        assert result.classification == MANUAL_NO_POSITIVE_STOCK
        assert result.adjustments == []

    def test_manual_when_positive_real_stock_is_insufficient(self):
        result = classify_item(
            item("LOW-POS"),
            [stock(10, -6, "0"), stock(11, 5, "A"), stock(12, 3, "PegNotIdentified")],
        )

        assert result is not None
        assert result.classification == MANUAL_INSUFFICIENT_POSITIVE_STOCK
        assert result.adjustments == []

    def test_manual_when_negative_is_in_real_location(self):
        result = classify_item(item("REAL-NEG"), [stock(10, -1, "A"), stock(11, 5, "B")])

        assert result is not None
        assert result.classification == MANUAL_REAL_NEGATIVE_LOCATION
        assert result.adjustments == []


class TestStockReconciliationCsv:
    def test_write_csv_includes_adjustments_and_manual_rows(self, tmp_path):
        auto = classify_item(item(), [stock(10, -2, "0"), stock(11, 10, "s1b")])
        manual = classify_item(item("REAL-NEG"), [stock(12, -1, "A"), stock(13, 5, "B")])
        assert auto is not None
        assert manual is not None

        path = tmp_path / "reconcile.csv"
        write_csv(path, [auto, manual])

        content = path.read_text()
        assert "AUTO_OFFSET_PLACEHOLDER" in content
        assert "MANUAL_REAL_NEGATIVE_LOCATION" in content
        assert "TC514400Z-80" in content
        assert "s1b" in content


class TestApplyStockAdjustmentBatchMigration:
    def test_rpc_migration_contains_required_safety_checks(self):
        path = Path(__file__).resolve().parents[1] / "supabase/migrations/20260502000003_apply_stock_adjustment_batch.sql"
        sql = path.read_text()

        assert "FOR UPDATE" in sql
        assert "Stale stock quantity" in sql
        assert "v_after < 0" in sql
        assert "INSERT INTO stock_adjustment" in sql
        assert "UPDATE stock" in sql
