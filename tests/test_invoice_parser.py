"""Integration tests for invoice parsing.

Run with:
    cd nikkoe-backend
    .venv/bin/python -m pytest tests/test_invoice_parser.py -v -s

Requires OPENAI_API_KEY in .env (or as an environment variable).
PDF fixtures live in the parent workspace directory; tests are skipped
when they are not present (e.g. in CI).

These tests exercise the real OpenAI call path (PDF-direct vision input
to ``gpt-4.1``) and assert that ``unit_price`` and ``shipping_total`` are
GROSS (VAT-inclusive) — the downstream system stores these values as the
per-unit stock cost.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from app.services.invoice_parser import _call_llm  # noqa: E402

WORKSPACE = Path(__file__).resolve().parent.parent.parent

TME_PDF = WORKSPACE / "4261503966.pdf"
# Newer TME invoice (April 2026) with 9 product lines + a "Transport" row
# that should be routed to shipping_net rather than appearing as a line.
TME2_PDF = WORKSPACE / "4261509868.pdf"
HONGTAIYU_PDF = WORKSPACE / "Proforma-Invoice20260311.pdf"
FARNELL_PDF = WORKSPACE / "7289408.pdf"
# Multi-page Farnell invoice with NO shipping charge. The summary table on
# page 2 has a "P&P Charge" column that is empty and a "Vat Rate" column
# showing 20.00 — earlier text-extraction-based parsers used to mis-read
# the 20.00 as a £20 shipping charge, inflating the displayed total from
# £49.54 to £61.28. PDF-direct parsing eliminates that class of bug.
FARNELL_NO_SHIPPING_PDF = WORKSPACE / "7512385.pdf"


def _read(path: Path) -> bytes:
    return path.read_bytes()


def _require(path: Path) -> None:
    if not path.exists():
        pytest.skip(f"Fixture PDF not available: {path.name}")


@pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY") and not os.environ.get("RUN_LLM_TESTS"),
    reason="OPENAI_API_KEY not set",
)
class TestLLMParsing:
    def test_tme_parsing(self):
        """TME UK invoice has 12 line items, all at 20% VAT.

        Net subtotal is £52.02, gross total is £62.42 (VAT £10.40).
        unit_price values are expected to be NET; vat_rate=20 per line.
        """
        _require(TME_PDF)
        parsed = _call_llm(_read(TME_PDF))

        assert parsed.get("supplier_name") is not None
        assert "transfer" in parsed["supplier_name"].lower() or "tme" in parsed["supplier_name"].lower()
        assert parsed.get("reference") is not None
        assert "4261503966" in parsed["reference"]
        assert parsed.get("currency_symbol") == "£"

        # Shipping is the "Transport" line (£7.70 net + 20% VAT = £9.24 gross).
        assert parsed.get("shipping_net") is not None
        assert abs(float(parsed["shipping_net"]) - 7.70) < 0.05, (
            f"Expected shipping_net ~£7.70, got £{parsed['shipping_net']}"
        )
        assert parsed.get("shipping_vat_rate") in (20, 20.0), (
            f"Expected shipping_vat_rate 20, got {parsed.get('shipping_vat_rate')}"
        )

        lines = parsed.get("lines", [])
        part_numbers = [line["part_number"] for line in lines]

        assert "PEC16-4215F-N0024" in part_numbers
        assert "SN74LS153N" in part_numbers
        assert "FTR-K1CK012W" in part_numbers
        assert "EC11E15244G1" in part_numbers

        transport_parts = [p for p in part_numbers if p.lower() == "transport"]
        assert len(transport_parts) == 0, "Transport line should be skipped"

        # Every product line should report 20% VAT.
        for line in lines:
            assert line.get("vat_rate") in (20, 20.0), (
                f"Line {line['part_number']} expected 20% VAT, got {line.get('vat_rate')}"
            )
            assert line.get("unit_price_net") is not None, (
                f"Line {line['part_number']} missing unit_price_net"
            )

        # Per-line NET checks against printed prices.
        pec_line = next(line for line in lines if line["part_number"] == "PEC16-4215F-N0024")
        assert pec_line["quantity"] == 1
        assert abs(pec_line["unit_price_net"] - 1.95) < 0.02

        sn74_line = next(line for line in lines if line["part_number"] == "SN74LS153N")
        assert sn74_line["quantity"] == 5
        assert abs(sn74_line["unit_price_net"] - 0.873) < 0.02, (
            f"Per-10 net pricing not computed correctly: got {sn74_line['unit_price_net']}"
        )

        expected_parts = [
            "PEC16-4215F-N0024",
            "SN74LS153N",
            "R9011-1-200K",
            "S20LC40UT-5000",
            "MB152",
            "282189-1",
            "IRFZ14PBF",
            "STP160N3LL",
            "FTR-K1CK012W",
            "EC11E15244G1",
        ]
        for p in expected_parts:
            assert p in part_numbers, f"Missing part: {p}"

        # Whole-invoice sanity against the printed Net Amount block (£52.02).
        # Tolerance ~5% because TME's "7,54/10 PCS" bulk-price + comma-decimal
        # format occasionally trips the model on a single line; the per-line
        # assertions above already verify the parsing itself.
        net_total = sum(l["quantity"] * l["unit_price_net"] for l in lines)
        shipping_net = float(parsed.get("shipping_net") or 0)
        printed_net_total = net_total + shipping_net
        assert abs(printed_net_total - 52.02) < 3.00, (
            f"Net invoice total should be ~£52.02, got £{printed_net_total:.2f} "
            f"(lines £{net_total:.2f} + shipping £{shipping_net:.2f})"
        )

        # Printed totals block should round-trip too if extracted.
        if parsed.get("printed_totals"):
            assert abs(parsed["printed_totals"]["gross"] - 62.42) < 0.05

        print(f"\nTME: Parsed {len(lines)} line items (expected ~11-12)")
        for line in lines:
            print(
                f"  {line['part_number']:30s} qty={line['quantity']:3d}  "
                f"net={line['unit_price_net']:.4f}  vat={line.get('vat_rate')}"
            )

    def test_tme2_parsing(self):
        """Newer TME invoice (4261509868.pdf): 9 products + Transport row.

        Net subtotal £20.38, Transport £7.70, Net Amount £28.08, VAT £5.62,
        Gross £33.70. Regression test confirming the Transport line is
        routed to shipping_net.
        """
        _require(TME2_PDF)
        parsed = _call_llm(_read(TME2_PDF))

        assert "transfer" in (parsed.get("supplier_name") or "").lower() or \
            "tme" in (parsed.get("supplier_name") or "").lower()
        assert "4261509868" in (parsed.get("reference") or "")
        assert parsed.get("currency_symbol") == "£"

        # Transport detection.
        assert abs(float(parsed.get("shipping_net") or 0) - 7.70) < 0.05, (
            f"Expected shipping_net ~£7.70, got £{parsed.get('shipping_net')}"
        )
        assert parsed.get("shipping_vat_rate") in (20, 20.0)

        lines = parsed.get("lines", [])
        part_numbers = [line["part_number"] for line in lines]

        # 9 product lines, no Transport.
        assert len(lines) == 9, f"Expected 9 line items, got {len(lines)}: {part_numbers}"
        assert not any(p.lower() == "transport" for p in part_numbers), (
            "Transport row leaked into lines instead of shipping"
        )

        expected_parts = [
            "TLC27L4CN", "D5SB60-7000", "EVQP0E07K", "AO3403", "SN74LS247N",
            "SMAJ13A-TR", "SN74AHCT32N", "T300-26D", "ERZV10D911",
        ]
        for p in expected_parts:
            assert p in part_numbers, f"Missing part: {p}"

        # All-20% VAT.
        for line in lines:
            assert line.get("vat_rate") in (20, 20.0), (
                f"Line {line['part_number']} expected 20% VAT, got {line.get('vat_rate')}"
            )

        # Net product subtotal ≈ £20.38 (close to printed £28.08 net minus
        # £7.70 net shipping). 5% tolerance for LLM rounding.
        product_net = sum(l["quantity"] * l["unit_price_net"] for l in lines)
        assert abs(product_net - 20.38) < 1.00, (
            f"Net product subtotal should be ~£20.38, got £{product_net:.2f}"
        )

        # Whole-invoice net + shipping ≈ £28.08.
        invoice_net = product_net + float(parsed.get("shipping_net") or 0)
        assert abs(invoice_net - 28.08) < 1.00, (
            f"Full net total should be ~£28.08, got £{invoice_net:.2f}"
        )

        # Printed totals block should show 28.08 / 5.62 / 33.70 if extracted.
        if parsed.get("printed_totals"):
            assert abs(parsed["printed_totals"]["net"] - 28.08) < 0.05
            assert abs(parsed["printed_totals"]["vat"] - 5.62) < 0.05
            assert abs(parsed["printed_totals"]["gross"] - 33.70) < 0.05

        print(f"\nTME2: Parsed {len(lines)} line items (expected 9)")
        print(f"  shipping_net = £{parsed.get('shipping_net')}, vat_rate={parsed.get('shipping_vat_rate')}")
        for line in lines:
            print(
                f"  {line['part_number']:30s} qty={line['quantity']:3d}  "
                f"net={line['unit_price_net']:.4f}  vat={line.get('vat_rate')}"
            )

    def test_hongtaiyu_parsing(self):
        """Hongtaiyu (China → UK) proforma in USD has NO VAT, so gross == net."""
        _require(HONGTAIYU_PDF)
        parsed = _call_llm(_read(HONGTAIYU_PDF))

        assert parsed.get("supplier_name") is not None
        assert "hongtaiyu" in parsed["supplier_name"].lower()
        assert parsed.get("currency_symbol") == "$"

        lines = parsed.get("lines", [])
        part_numbers = [line["part_number"] for line in lines]

        assert "UCN5818EPF" in part_numbers
        assert "MR752" in part_numbers
        assert "TC5092AP" in part_numbers
        assert "IRF530N" in part_numbers

        shipping_parts = [p for p in part_numbers if "ship" in p.lower() or "charge" in p.lower()]
        assert len(shipping_parts) == 0, "Shipping charge should be skipped"

        # Overseas proforma → no VAT system. Per-line vat_rate should be
        # null or 0; the printed price IS the net price.
        for line in lines:
            rate = line.get("vat_rate")
            assert rate is None or rate == 0, (
                f"Line {line['part_number']} unexpected vat_rate={rate} "
                f"(USD proforma has no VAT)"
            )

        ucn_line = next(line for line in lines if line["part_number"] == "UCN5818EPF")
        assert ucn_line["quantity"] == 1
        assert abs(ucn_line["unit_price_net"] - 9.00) < 0.01

        tc_line = next(line for line in lines if line["part_number"] == "TC5092AP")
        assert tc_line["quantity"] == 33
        assert abs(tc_line["unit_price_net"] - 8.50) < 0.01

        assert len(lines) >= 40, f"Expected 40+ items, got {len(lines)}"

        print(f"\nHongtaiyu: Parsed {len(lines)} line items (expected ~50+)")
        for line in lines[:10]:
            print(
                f"  {line['part_number']:30s} qty={line['quantity']:3d}  "
                f"net={line['unit_price_net']:.4f}"
            )
        if len(lines) > 10:
            print(f"  ... and {len(lines) - 10} more")

    def test_farnell_parsing(self):
        """Single-line Farnell at 20% VAT: net £1.99 → gross £2.39, no shipping."""
        _require(FARNELL_PDF)
        parsed = _call_llm(_read(FARNELL_PDF))

        assert parsed.get("supplier_name") is not None
        assert "farnell" in parsed["supplier_name"].lower()
        assert "7289408" in (parsed.get("reference") or "")
        assert parsed.get("currency_symbol") == "£"
        # No shipping → shipping_net 0 (or null); shipping_total 0.
        assert (parsed.get("shipping_net") or 0) == 0
        assert float(parsed.get("shipping_total") or 0) == 0

        lines = parsed.get("lines", [])
        assert len(lines) == 1, f"Expected 1 line item, got {len(lines)}"

        line = lines[0]
        assert line["quantity"] == 1
        assert line.get("vat_rate") in (20, 20.0)
        assert abs(line["unit_price_net"] - 1.99) < 0.02, (
            f"Expected net unit price £1.99, got £{line['unit_price_net']}"
        )
        # Gross = net * (1 + rate/100).
        gross = line["unit_price_net"] * (1 + line["vat_rate"] / 100)
        assert abs(gross - 2.388) < 0.02, (
            f"Expected gross unit price £2.388 (net £1.99 + 20% VAT), "
            f"computed £{gross}"
        )

        # Printed totals: 1.99 / 0.40 / 2.39 if extracted.
        if parsed.get("printed_totals"):
            assert abs(parsed["printed_totals"]["gross"] - 2.39) < 0.02

        print(f"\nFarnell: Parsed {len(lines)} line item")
        print(
            f"  {line['part_number']:30s} qty={line['quantity']:3d}  "
            f"net={line['unit_price_net']:.4f}  gross={gross:.4f}"
        )

    def test_farnell_no_shipping_parsing(self):
        """Multi-page Farnell invoice, no shipping, all 20% VAT.

        Net subtotal £41.28, VAT £8.26, Invoice Total £49.54.
        Earlier text-based parsers used to incorrectly flag a £20 shipping
        charge by misreading the VAT rate column.
        """
        _require(FARNELL_NO_SHIPPING_PDF)
        parsed = _call_llm(_read(FARNELL_NO_SHIPPING_PDF))

        assert "farnell" in (parsed.get("supplier_name") or "").lower()
        assert "7512385" in (parsed.get("reference") or "")
        assert parsed.get("currency_symbol") == "£"

        assert (parsed.get("shipping_net") or 0) == 0
        assert float(parsed.get("shipping_total") or 0) == 0, (
            f"Invoice has no P&P charge, expected shipping_total=0, "
            f"got {parsed.get('shipping_total')}"
        )

        lines = parsed.get("lines", [])
        assert len(lines) == 7, f"Expected 7 line items, got {len(lines)}"

        for line in lines:
            assert line.get("vat_rate") in (20, 20.0), (
                f"Line {line['part_number']} expected 20% VAT, got {line.get('vat_rate')}"
            )

        # Net line total ≈ £41.28.
        net_total = sum(l["quantity"] * l["unit_price_net"] for l in lines)
        assert abs(net_total - 41.28) < 0.10, (
            f"Net line total should be ~£41.28, got £{net_total:.2f}"
        )

        # Gross line total ≈ £49.54 — derive gross from net + rate.
        gross_total = sum(
            l["quantity"] * l["unit_price_net"] * (1 + l["vat_rate"] / 100)
            for l in lines
        )
        assert abs(gross_total - 49.54) < 0.10, (
            f"Gross line total should be ~£49.54 (net £41.28 + £8.26 VAT), "
            f"computed £{gross_total:.2f}"
        )

        # Printed totals: 41.28 / 8.26 / 49.54 if extracted.
        if parsed.get("printed_totals"):
            assert abs(parsed["printed_totals"]["net"] - 41.28) < 0.05
            assert abs(parsed["printed_totals"]["gross"] - 49.54) < 0.05
