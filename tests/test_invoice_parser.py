"""Integration tests for invoice parsing.

Run with:
    cd nikkoe-backend
    .venv/bin/python -m pytest tests/test_invoice_parser.py -v -s

Requires OPENAI_API_KEY in .env (or as an environment variable).
PDF fixtures live in the parent workspace directory; tests are skipped
when they are not present (e.g. in CI).
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from app.services.invoice_parser import _call_llm, extract_text_from_pdf  # noqa: E402

WORKSPACE = Path(__file__).resolve().parent.parent.parent

TME_PDF = WORKSPACE / "4261503966.pdf"
HONGTAIYU_PDF = WORKSPACE / "Proforma-Invoice20260311.pdf"
FARNELL_PDF = WORKSPACE / "7289408.pdf"
# Multi-page Farnell invoice with NO shipping charge. The summary table on
# page 2 has a "P&P Charge" column that is empty and a "Vat Rate" column
# showing 20.00 — the parser used to mis-read the 20.00 as a £20 shipping
# charge, inflating the displayed total from £49.54 to £61.28.
FARNELL_NO_SHIPPING_PDF = WORKSPACE / "7512385.pdf"


def _read(path: Path) -> bytes:
    return path.read_bytes()


def _require(path: Path) -> None:
    if not path.exists():
        pytest.skip(f"Fixture PDF not available: {path.name}")


class TestTextExtraction:
    def test_tme_extraction(self):
        _require(TME_PDF)
        text = extract_text_from_pdf(_read(TME_PDF))
        assert "PEC16-4215F-N0024" in text
        assert "SN74LS153N" in text
        assert "Invoice no.: 4261503966" in text
        assert "Transfer Multisort Elektronik" in text

    def test_hongtaiyu_extraction(self):
        _require(HONGTAIYU_PDF)
        text = extract_text_from_pdf(_read(HONGTAIYU_PDF))
        assert "UCN5818EPF" in text
        assert "TC5092AP" in text
        # Layout-preserving extraction may insert multiple spaces between
        # words when reconstructing column alignment, so match flexibly.
        assert re.search(r"HK\s+Hongtaiyu", text)

    def test_farnell_extraction(self):
        _require(FARNELL_PDF)
        text = extract_text_from_pdf(_read(FARNELL_PDF))
        assert "1892676" in text
        assert "Premier Farnell" in text


@pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY") and not os.environ.get("RUN_LLM_TESTS"),
    reason="OPENAI_API_KEY not set",
)
class TestLLMParsing:
    def test_tme_parsing(self):
        _require(TME_PDF)
        text = extract_text_from_pdf(_read(TME_PDF))
        parsed = _call_llm(text)

        assert parsed.get("supplier_name") is not None
        assert "transfer" in parsed["supplier_name"].lower() or "tme" in parsed["supplier_name"].lower()
        assert parsed.get("reference") is not None
        assert "4261503966" in parsed["reference"]
        assert parsed.get("currency_symbol") == "£"

        lines = parsed.get("lines", [])
        part_numbers = [line["part_number"] for line in lines]

        assert "PEC16-4215F-N0024" in part_numbers
        assert "SN74LS153N" in part_numbers
        assert "FTR-K1CK012W" in part_numbers
        assert "EC11E15244G1" in part_numbers

        transport_parts = [p for p in part_numbers if p.lower() == "transport"]
        assert len(transport_parts) == 0, "Transport line should be skipped"

        pec_line = next(line for line in lines if line["part_number"] == "PEC16-4215F-N0024")
        assert pec_line["quantity"] == 1
        assert abs(pec_line["unit_price"] - 1.95) < 0.01

        sn74_line = next(line for line in lines if line["part_number"] == "SN74LS153N")
        assert sn74_line["quantity"] == 5
        assert abs(sn74_line["unit_price"] - 0.873) < 0.01, (
            f"Per-10 pricing not computed correctly: got {sn74_line['unit_price']}"
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

        capacitor_line = next(
            (line for line in lines if "16" in line["part_number"] and "17" in line["part_number"]),
            None,
        )
        if capacitor_line:
            assert capacitor_line["quantity"] == 5
            assert abs(capacitor_line["unit_price"] - 3.30) < 0.01

        print(f"\nTME: Parsed {len(lines)} line items (expected ~11-12)")
        for line in lines:
            print(f"  {line['part_number']:30s} qty={line['quantity']:3d}  unit_price={line['unit_price']:.4f}")

    def test_hongtaiyu_parsing(self):
        _require(HONGTAIYU_PDF)
        text = extract_text_from_pdf(_read(HONGTAIYU_PDF))
        parsed = _call_llm(text)

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

        ucn_line = next(line for line in lines if line["part_number"] == "UCN5818EPF")
        assert ucn_line["quantity"] == 1
        assert abs(ucn_line["unit_price"] - 9.00) < 0.01

        tc_line = next(line for line in lines if line["part_number"] == "TC5092AP")
        assert tc_line["quantity"] == 33
        assert abs(tc_line["unit_price"] - 8.50) < 0.01

        assert len(lines) >= 40, f"Expected 40+ items, got {len(lines)}"

        print(f"\nHongtaiyu: Parsed {len(lines)} line items (expected ~50+)")
        for line in lines[:10]:
            print(f"  {line['part_number']:30s} qty={line['quantity']:3d}  unit_price={line['unit_price']:.4f}")
        if len(lines) > 10:
            print(f"  ... and {len(lines) - 10} more")

    def test_farnell_parsing(self):
        """Generalizability test -- this invoice was NOT used during development."""
        _require(FARNELL_PDF)
        text = extract_text_from_pdf(_read(FARNELL_PDF))
        parsed = _call_llm(text)

        assert parsed.get("supplier_name") is not None
        assert "farnell" in parsed["supplier_name"].lower()
        assert "7289408" in (parsed.get("reference") or "")
        assert parsed.get("currency_symbol") == "£"

        lines = parsed.get("lines", [])
        assert len(lines) == 1, f"Expected 1 line item, got {len(lines)}"

        line = lines[0]
        assert line["quantity"] == 1
        assert abs(line["unit_price"] - 1.99) < 0.01

        print(f"\nFarnell: Parsed {len(lines)} line item")
        print(f"  {line['part_number']:30s} qty={line['quantity']:3d}  unit_price={line['unit_price']:.4f}")

    def test_farnell_no_shipping_parsing(self):
        """Regression: multi-page Farnell invoice with empty P&P column.

        The flat (non-layout) pdfplumber extractor used to drop the empty
        P&P Charge column from the summary table, which caused the LLM to
        misalign columns and read the VAT rate "20.00" as a £20 shipping
        charge. Layout-preserving extraction keeps the empty column intact
        so shipping_total is correctly 0.
        """
        _require(FARNELL_NO_SHIPPING_PDF)
        text = extract_text_from_pdf(_read(FARNELL_NO_SHIPPING_PDF))
        parsed = _call_llm(text)

        assert "farnell" in (parsed.get("supplier_name") or "").lower()
        assert "7512385" in (parsed.get("reference") or "")
        assert parsed.get("currency_symbol") == "£"

        assert parsed.get("shipping_total") == 0, (
            f"Invoice has no P&P charge, expected shipping_total=0, "
            f"got {parsed.get('shipping_total')}"
        )

        lines = parsed.get("lines", [])
        assert len(lines) == 7, f"Expected 7 line items, got {len(lines)}"

        line_subtotal = sum(l["quantity"] * l["unit_price"] for l in lines)
        assert abs(line_subtotal - 41.28) < 0.05, (
            f"Line subtotal should be ~£41.28, got £{line_subtotal:.2f}"
        )
