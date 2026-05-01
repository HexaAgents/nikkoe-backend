from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.errors import AppError
from app.schemas import ParseInvoiceResponse, ResolvedLineItem
from app.services.invoice_parser import (
    _coerce_decimal,
    _coerce_printed_totals,
    _coerce_rate,
    _coerce_shipping_total,
    _gross_from_net,
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
        result = _resolve_items([{"part_number": "SN74LS153N", "quantity": 5, "unit_price_net": 0.873, "vat_rate": 20}])
        assert len(result) == 1
        assert result[0].matched_item_id == 42
        assert result[0].quantity == 5
        assert result[0].unit_price_net == 0.873
        assert result[0].vat_rate == 20
        assert abs(result[0].unit_price - 1.0476) < 1e-4  # 0.873 * 1.20

    @patch("app.services.invoice_parser.supabase")
    def test_unmatched_item(self, mock_sb):
        mock_sb.table.return_value.select.return_value.filter.return_value.limit.return_value.execute.return_value = (
            MagicMock(data=[])
        )
        result = _resolve_items([{"part_number": "UNKNOWN", "quantity": 1, "unit_price_net": 0, "vat_rate": 20}])
        assert result[0].matched_item_id is None

    def test_empty_part_number_skips_lookup(self):
        result = _resolve_items([{"part_number": "", "quantity": 2, "unit_price_net": 1.0, "vat_rate": 20}])
        assert result[0].matched_item_id is None
        assert result[0].quantity == 2
        assert result[0].vat_rate == 20

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
        result = _resolve_items([{"part_number": "ABC123", "quantity": 1, "unit_price_net": 1.0, "vat_rate": 20}])
        assert result[0].matched_item_id == 2

    @patch("app.services.invoice_parser.supabase")
    def test_handles_db_exception(self, mock_sb):
        mock_sb.table.side_effect = Exception("db error")
        result = _resolve_items([{"part_number": "ERR", "quantity": 1, "unit_price_net": 1.0, "vat_rate": 20}])
        assert result[0].matched_item_id is None

    def test_no_vat_rate_treated_as_zero(self):
        """Overseas proforma with no VAT system → unit_price == unit_price_net."""
        result = _resolve_items([{"part_number": "FOO", "quantity": 1, "unit_price_net": 9.0, "vat_rate": None}])
        assert result[0].vat_rate is None
        assert result[0].unit_price_net == 9.0
        assert result[0].unit_price == 9.0  # net * 1.00

    def test_falls_back_to_unit_price_when_net_missing(self):
        """Defensive: if LLM only emits legacy unit_price (no net), keep it as gross."""
        result = _resolve_items([{"part_number": "X", "quantity": 1, "unit_price": 2.5}])
        assert result[0].unit_price == 2.5
        assert result[0].unit_price_net is None


class TestCoerceShippingTotal:
    def test_none_returns_zero(self):
        assert _coerce_shipping_total(None) == 0.0

    def test_numeric_passthrough(self):
        assert _coerce_shipping_total(12.5) == 12.5

    def test_numeric_string_parsed(self):
        assert _coerce_shipping_total("7.99") == 7.99

    def test_non_numeric_returns_zero(self):
        assert _coerce_shipping_total("free") == 0.0

    def test_negative_returns_zero(self):
        assert _coerce_shipping_total(-3.0) == 0.0

    def test_rounds_to_four_decimals(self):
        assert _coerce_shipping_total(1.234567) == 1.2346


class TestCoerceDecimal:
    def test_none_returns_none(self):
        assert _coerce_decimal(None) is None

    def test_numeric_passthrough(self):
        assert _coerce_decimal(2.5) == 2.5

    def test_numeric_string_parsed(self):
        assert _coerce_decimal("0.873") == 0.873

    def test_non_numeric_returns_none(self):
        assert _coerce_decimal("nope") is None

    def test_negative_returns_none(self):
        assert _coerce_decimal(-1.0) is None

    def test_rounds_to_four_decimals(self):
        assert _coerce_decimal(0.123456789) == 0.1235


class TestCoerceRate:
    def test_none_returns_none(self):
        assert _coerce_rate(None) is None

    def test_integer_passthrough(self):
        assert _coerce_rate(20) == 20.0

    def test_decimal_string_parsed(self):
        assert _coerce_rate("20.00") == 20.0

    def test_strips_percent_suffix(self):
        assert _coerce_rate("5%") == 5.0

    def test_zero_is_valid(self):
        assert _coerce_rate(0) == 0.0

    def test_negative_returns_none(self):
        assert _coerce_rate(-5) is None

    def test_non_numeric_returns_none(self):
        assert _coerce_rate("standard") is None

    def test_empty_string_returns_none(self):
        assert _coerce_rate("") is None


class TestGrossFromNet:
    def test_zero_rate_returns_net(self):
        assert _gross_from_net(10.0, 0) == 10.0

    def test_none_rate_returns_net(self):
        assert _gross_from_net(10.0, None) == 10.0

    def test_none_net_returns_zero(self):
        assert _gross_from_net(None, 20) == 0.0

    def test_twenty_percent_grosses_up(self):
        assert _gross_from_net(0.873, 20) == 1.0476

    def test_rounds_to_four_decimals(self):
        result = _gross_from_net(0.123456, 20)
        assert result == round(0.123456 * 1.20, 4)


class TestCoercePrintedTotals:
    def test_none_returns_none(self):
        assert _coerce_printed_totals(None) is None

    def test_non_dict_returns_none(self):
        assert _coerce_printed_totals("not a dict") is None
        assert _coerce_printed_totals([1, 2, 3]) is None

    def test_valid_block_parses(self):
        result = _coerce_printed_totals({"net": 41.28, "vat": 8.26, "gross": 49.54})
        assert result is not None
        assert result.net == 41.28
        assert result.vat == 8.26
        assert result.gross == 49.54

    def test_string_values_coerced(self):
        result = _coerce_printed_totals({"net": "28.08", "vat": "5.62", "gross": "33.70"})
        assert result is not None
        assert result.net == 28.08

    def test_missing_field_returns_none(self):
        assert _coerce_printed_totals({"net": 1.0, "vat": 0.2}) is None

    def test_negative_field_returns_none(self):
        assert _coerce_printed_totals({"net": -1.0, "vat": 0.2, "gross": 1.2}) is None


class TestParseInvoice:
    @patch("app.services.invoice_parser._resolve_items")
    @patch("app.services.invoice_parser._resolve_supplier", return_value=10)
    @patch("app.services.invoice_parser._call_llm")
    def test_happy_path(self, mock_llm, _mock_supplier, mock_items):
        mock_llm.return_value = {
            "supplier_name": "TME",
            "reference": "123",
            "currency_symbol": "£",
            "shipping_net": 4.25,
            "shipping_vat_rate": 20,
            "printed_totals": {"net": 28.08, "vat": 5.62, "gross": 33.70},
            "lines": [{"part_number": "X", "quantity": 1, "unit_price_net": 1.0, "vat_rate": 20}],
        }
        mock_items.return_value = [
            ResolvedLineItem(
                part_number="X",
                quantity=1,
                unit_price=1.20,
                unit_price_net=1.0,
                vat_rate=20,
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
        # shipping_total is gross (net 4.25 + 20% VAT = 5.10).
        assert result.shipping_total == 5.10
        assert result.shipping_net == 4.25
        assert result.shipping_vat_rate == 20
        assert result.printed_totals is not None
        assert result.printed_totals.gross == 33.70
        assert len(result.lines) == 1
        # Verify the LLM was called with the raw bytes (no text extraction step).
        mock_llm.assert_called_once_with(b"fake-pdf")

    @patch("app.services.invoice_parser._resolve_items", return_value=[])
    @patch("app.services.invoice_parser._resolve_supplier", return_value=None)
    @patch("app.services.invoice_parser._call_llm")
    def test_missing_shipping_defaults_to_zero(self, mock_llm, _sup, _items):
        mock_llm.return_value = {
            "supplier_name": None,
            "reference": None,
            "currency_symbol": "£",
            "lines": [],
        }
        result = parse_invoice(b"fake-pdf")
        assert result.shipping_total == 0.0
        assert result.shipping_net == 0.0
        assert result.shipping_vat_rate is None
        assert result.printed_totals is None

    @patch("app.services.invoice_parser._resolve_items", return_value=[])
    @patch("app.services.invoice_parser._resolve_supplier", return_value=None)
    @patch("app.services.invoice_parser._call_llm")
    def test_legacy_shipping_total_is_honored(self, mock_llm, _sup, _items):
        """Defensive fallback: if the LLM only emits the legacy shipping_total
        (no shipping_net), we treat it as gross and don't multiply it again."""
        mock_llm.return_value = {
            "currency_symbol": "£",
            "shipping_total": 9.24,  # already gross
            "lines": [],
        }
        result = parse_invoice(b"fake-pdf")
        assert result.shipping_total == 9.24
        assert result.shipping_net == 0.0  # not provided

    def test_raises_on_empty_pdf(self):
        with pytest.raises(AppError, match="Empty PDF"):
            parse_invoice(b"")


class TestParseInvoiceStream:
    @patch("app.services.invoice_parser._resolve_location", return_value=(3, "BIN-1"))
    @patch("app.services.invoice_parser.supabase")
    @patch("app.services.invoice_parser._resolve_supplier", return_value=5)
    @patch("app.services.invoice_parser._call_llm")
    def test_yields_header_lines_done(self, mock_llm, _sup, mock_sb, _loc):
        mock_llm.return_value = {
            "supplier_name": "Acme",
            "reference": "INV-1",
            "currency_symbol": "£",
            "shipping_net": 7.70,
            "shipping_vat_rate": 20,
            "printed_totals": {"net": 28.08, "vat": 5.62, "gross": 33.70},
            "lines": [{"part_number": "P1", "quantity": 2, "unit_price_net": 3.0, "vat_rate": 20}],
        }
        mock_sb.table.return_value.select.return_value.filter.return_value.limit.return_value.execute.return_value = (
            MagicMock(data=[{"id": 99, "item_id": "P1"}])
        )

        events = list(parse_invoice_stream(b"pdf-bytes"))
        header_events = [e for e in events if "event: header" in e]
        assert len(header_events) == 1
        # Header carries gross shipping (net 7.70 + 20% VAT = 9.24) plus net + rate.
        assert '"shipping_total": 9.24' in header_events[0]
        assert '"shipping_net": 7.7' in header_events[0]
        assert '"shipping_vat_rate": 20' in header_events[0]
        assert '"printed_totals":' in header_events[0]
        assert '"gross": 33.7' in header_events[0]
        line_events = [e for e in events if "event: line" in e]
        assert len(line_events) == 1
        # Line carries gross unit_price (3.0 + 20% = 3.6) plus net + rate.
        assert '"unit_price": 3.6' in line_events[0]
        assert '"unit_price_net": 3.0' in line_events[0]
        assert '"vat_rate": 20' in line_events[0]
        assert any("event: done" in e for e in events)
        mock_llm.assert_called_once_with(b"pdf-bytes")

    def test_yields_error_on_empty_pdf(self):
        events = list(parse_invoice_stream(b""))
        assert len(events) == 1
        assert "error" in events[0]
        assert "Empty PDF" in events[0]

    @patch("app.services.invoice_parser._call_llm", side_effect=AppError(500, "broken"))
    def test_yields_error_on_app_error(self, _llm):
        events = list(parse_invoice_stream(b"bad"))
        assert any("broken" in e for e in events)

    @patch("app.services.invoice_parser._call_llm", side_effect=RuntimeError("boom"))
    def test_yields_error_on_unexpected_exception(self, _llm):
        events = list(parse_invoice_stream(b"bad"))
        assert any("boom" in e for e in events)
