from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.errors import AppError
from app.schemas import ParseInvoiceResponse, ResolvedLineItem
from app.services.invoice_parser import (
    _resolve_items,
    _resolve_location,
    _resolve_supplier,
    _sse,
    parse_invoice,
    parse_invoice_stream,
)


class TestSse:
    def test_formats_event_and_data(self):
        result = _sse("header", {"key": "val"})
        assert result.startswith("event: header\n")
        assert '"key": "val"' in result
        assert result.endswith("\n\n")


class TestResolveSupplier:
    def test_returns_none_for_none_name(self):
        assert _resolve_supplier(None) is None

    def test_returns_none_for_empty_name(self):
        assert _resolve_supplier("") is None

    @patch("app.services.invoice_parser.supabase")
    def test_returns_id_on_exact_match(self, mock_sb):
        mock_sb.table.return_value.select.return_value.ilike.return_value.limit.return_value.execute.return_value = (
            MagicMock(data=[{"id": 10, "name": "Acme Corp"}, {"id": 11, "name": "Acme Corp Inc"}])
        )
        assert _resolve_supplier("Acme Corp") == 10

    @patch("app.services.invoice_parser.supabase")
    def test_returns_first_when_no_exact(self, mock_sb):
        mock_sb.table.return_value.select.return_value.ilike.return_value.limit.return_value.execute.return_value = (
            MagicMock(data=[{"id": 20, "name": "Foo Industries"}])
        )
        assert _resolve_supplier("Foo") == 20

    @patch("app.services.invoice_parser.supabase")
    def test_returns_none_on_empty_result(self, mock_sb):
        mock_sb.table.return_value.select.return_value.ilike.return_value.limit.return_value.execute.return_value = (
            MagicMock(data=[])
        )
        assert _resolve_supplier("Missing") is None

    @patch("app.services.invoice_parser.supabase")
    def test_returns_none_on_exception(self, mock_sb):
        mock_sb.table.side_effect = Exception("db error")
        assert _resolve_supplier("Err") is None


def _stock_query(mock_sb):
    """Traverse the chained Supabase query builder for stock table."""
    chain = mock_sb.table.return_value.select.return_value
    chain = chain.eq.return_value.gt.return_value
    return chain.order.return_value.limit.return_value.execute


class TestResolveLocation:
    @patch("app.services.invoice_parser.supabase")
    def test_returns_location_for_item(self, mock_sb):
        _stock_query(mock_sb).return_value = MagicMock(
            data=[{"location_id": 5, "quantity": 100, "location": {"code": "BIN-A1"}}]
        )
        loc_id, loc_code = _resolve_location(1)
        assert loc_id == 5
        assert loc_code == "BIN-A1"

    @patch("app.services.invoice_parser.supabase")
    def test_returns_none_when_no_stock(self, mock_sb):
        _stock_query(mock_sb).return_value = MagicMock(data=[])
        loc_id, loc_code = _resolve_location(1)
        assert loc_id is None
        assert loc_code is None

    @patch("app.services.invoice_parser.supabase")
    def test_returns_none_on_exception(self, mock_sb):
        mock_sb.table.side_effect = Exception("db error")
        loc_id, loc_code = _resolve_location(1)
        assert loc_id is None
        assert loc_code is None

    @patch("app.services.invoice_parser.supabase")
    def test_handles_missing_location_relation(self, mock_sb):
        _stock_query(mock_sb).return_value = MagicMock(data=[{"location_id": 7, "quantity": 50, "location": None}])
        loc_id, loc_code = _resolve_location(1)
        assert loc_id == 7
        assert loc_code is None


class TestResolveItems:
    @patch("app.services.invoice_parser._resolve_location", return_value=(None, None))
    @patch("app.services.invoice_parser.supabase")
    def test_resolves_matching_item(self, mock_sb, _mock_loc):
        mock_sb.table.return_value.select.return_value.filter.return_value.limit.return_value.execute.return_value = (
            MagicMock(data=[{"id": 42, "item_id": "SN74LS153N"}])
        )
        result = _resolve_items([{"part_number": "SN74LS153N", "quantity": 5, "unit_price": 0.873}])
        assert len(result) == 1
        assert result[0].matched_item_id == 42
        assert result[0].quantity == 5

    @patch("app.services.invoice_parser.supabase")
    def test_unmatched_item(self, mock_sb):
        mock_sb.table.return_value.select.return_value.filter.return_value.limit.return_value.execute.return_value = (
            MagicMock(data=[])
        )
        result = _resolve_items([{"part_number": "UNKNOWN", "quantity": 1, "unit_price": 0}])
        assert result[0].matched_item_id is None

    def test_empty_part_number_skips_lookup(self):
        result = _resolve_items([{"part_number": "", "quantity": 2, "unit_price": 1.0}])
        assert result[0].matched_item_id is None
        assert result[0].quantity == 2

    def test_empty_lines(self):
        assert _resolve_items([]) == []

    @patch("app.services.invoice_parser._resolve_location", return_value=(None, None))
    @patch("app.services.invoice_parser.supabase")
    def test_prefers_exact_match(self, mock_sb, _mock_loc):
        mock_sb.table.return_value.select.return_value.filter.return_value.limit.return_value.execute.return_value = (
            MagicMock(
                data=[
                    {"id": 1, "item_id": "ABC123X"},
                    {"id": 2, "item_id": "ABC123"},
                ]
            )
        )
        result = _resolve_items([{"part_number": "ABC123", "quantity": 1, "unit_price": 1.0}])
        assert result[0].matched_item_id == 2

    @patch("app.services.invoice_parser.supabase")
    def test_handles_db_exception(self, mock_sb):
        mock_sb.table.side_effect = Exception("db error")
        result = _resolve_items([{"part_number": "ERR", "quantity": 1, "unit_price": 1.0}])
        assert result[0].matched_item_id is None


class TestParseInvoice:
    @patch("app.services.invoice_parser._resolve_items")
    @patch("app.services.invoice_parser._resolve_supplier", return_value=10)
    @patch("app.services.invoice_parser._call_llm")
    @patch("app.services.invoice_parser.extract_text_from_pdf", return_value="Invoice text here")
    def test_happy_path(self, _mock_pdf, mock_llm, _mock_supplier, mock_items):
        mock_llm.return_value = {
            "supplier_name": "TME",
            "reference": "123",
            "currency_symbol": "£",
            "lines": [{"part_number": "X", "quantity": 1, "unit_price": 1.0}],
        }
        mock_items.return_value = [
            ResolvedLineItem(
                part_number="X",
                quantity=1,
                unit_price=1.0,
                matched_item_id=None,
                matched_item_name=None,
                matched_location_id=None,
                matched_location_code=None,
            )
        ]
        result = parse_invoice(b"fake-pdf")
        assert isinstance(result, ParseInvoiceResponse)
        assert result.supplier_name == "TME"
        assert result.matched_supplier_id == 10
        assert len(result.lines) == 1

    @patch("app.services.invoice_parser.extract_text_from_pdf", return_value="   ")
    def test_raises_on_empty_text(self, _mock_pdf):
        with pytest.raises(AppError, match="Could not extract any text"):
            parse_invoice(b"empty-pdf")


class TestParseInvoiceStream:
    @patch("app.services.invoice_parser._resolve_location", return_value=(3, "BIN-1"))
    @patch("app.services.invoice_parser.supabase")
    @patch("app.services.invoice_parser._resolve_supplier", return_value=5)
    @patch("app.services.invoice_parser._call_llm")
    @patch("app.services.invoice_parser.extract_text_from_pdf", return_value="Invoice text")
    def test_yields_header_lines_done(self, _pdf, mock_llm, _sup, mock_sb, _loc):
        mock_llm.return_value = {
            "supplier_name": "Acme",
            "reference": "INV-1",
            "currency_symbol": "$",
            "lines": [{"part_number": "P1", "quantity": 2, "unit_price": 3.5}],
        }
        mock_sb.table.return_value.select.return_value.filter.return_value.limit.return_value.execute.return_value = (
            MagicMock(data=[{"id": 99, "item_id": "P1"}])
        )

        events = list(parse_invoice_stream(b"pdf-bytes"))
        assert any("header" in e for e in events)
        assert any("line" in e for e in events)
        assert any("done" in e for e in events)

    @patch("app.services.invoice_parser.extract_text_from_pdf", return_value="  ")
    def test_yields_error_on_empty_pdf(self, _pdf):
        events = list(parse_invoice_stream(b"empty"))
        assert len(events) == 1
        assert "error" in events[0]

    @patch("app.services.invoice_parser.extract_text_from_pdf", side_effect=AppError(500, "broken"))
    def test_yields_error_on_app_error(self, _pdf):
        events = list(parse_invoice_stream(b"bad"))
        assert any("broken" in e for e in events)

    @patch("app.services.invoice_parser.extract_text_from_pdf", side_effect=RuntimeError("boom"))
    def test_yields_error_on_unexpected_exception(self, _pdf):
        events = list(parse_invoice_stream(b"bad"))
        assert any("boom" in e for e in events)
