from __future__ import annotations

import base64
import json

from openai import OpenAI

from app.config import settings
from app.dependencies import supabase
from app.errors import AppError
from app.repositories.base import dash_insensitive_pattern
from app.repositories.supplier_alias import SupplierAliasRepository
from app.repositories.supplier_quote import SupplierQuoteRepository
from app.schemas import ParseInvoiceResponse, PrintedTotals, ResolvedLineItem

_alias_repo = SupplierAliasRepository()
_supplier_quote_repo = SupplierQuoteRepository()

# We send the PDF directly to a vision-capable model rather than extracting
# text first. Text extraction (even with layout=True) silently mangles
# multi-column summary tables on real-world invoices (e.g. the Farnell
# "Vat Rate | Goods | Vat | P&P Charge" block). Letting the model see the
# rendered page eliminates the entire class of layout-flattening bugs.
_MODEL = "gpt-4.1"

_SYSTEM_PROMPT = """\
You are an invoice parser for an electronics parts distributor.
You will be given a PDF invoice as a file input. Read it directly,
including its tables, columns and totals block, and return structured JSON.

You return NET prices and VAT rates separately. The backend computes the
gross (VAT-inclusive) price from these — it does NOT trust any pre-grossed
value from you, so DO NOT round gross prices yourself.

Rules:

1. "lines" must contain ONLY physical product / component line items. DO NOT
   put shipping, transport, carriage, postage (P&P), delivery, bank charges,
   handling or insurance rows into "lines". On TME invoices the row literally
   labelled "Transport" is shipping, NOT a product line — it goes into
   shipping_net / shipping_vat_rate.

2. "unit_price_net" is the NET (VAT-EXCLUSIVE) price per single unit, as a
   decimal number in the invoice currency.
   - If the invoice prints "Net Price" per unit, use that.
   - If the invoice shows a bulk price like "8,73/10 PCS", compute per-unit:
     8.73 / 10 = 0.873.
   - Convert European comma decimals to dots: "1,95" → 1.95.
   - If the invoice has no VAT at all (e.g. proforma from a non-VAT
     registered overseas supplier), report the printed unit price as the
     net price.

3. "vat_rate" is the per-line VAT rate as a number (e.g. 20 for 20%, 5 for
   5%, 0 for zero-rated). Use null only when the invoice has no VAT system
   at all (overseas proforma). Do not embed the % sign.

4. "shipping_net" is the NET sum of all shipping / freight / carriage /
   postage (P&P) / delivery / transport charges (TME's "Transport" row
   counts here), as a single decimal number in the invoice currency.
   Return 0 if the invoice shows no shipping charge.
   - CRITICAL: A label like "P&P Charge", "Shipping", "Carriage", or
     "Delivery" with NO numeric value next to it means there is NO shipping
     charge — return 0. Do NOT borrow a number from a different column
     (VAT rate %, goods subtotal, VAT amount, etc.) just because a shipping
     label exists on the page.
   - A "Vat Rate" of "20.00" (a percentage) is NEVER the shipping amount.

5. "shipping_vat_rate" is the VAT rate applied to shipping (typically the
   same as the line VAT rate on UK invoices). Return null when there is no
   shipping or no VAT.

6. "printed_totals" is the invoice's own Net / VAT / Gross totals block
   (e.g. TME's `Net Amount %VAT VAT Gross amount  28,08 20 5,62 33,70` or
   Farnell's `Invoice Subtotal 41.28  Vat 8.26  Invoice Total GBP 49.54`).
   Return:
       { "net": decimal, "vat": decimal, "gross": decimal }
   when the block is printed; otherwise null. These let the UI cross-check
   our per-line maths against what the invoice itself states.

7. "part_number" must be the manufacturer or distributor part number exactly
   as printed (e.g. "SN74LS153N", "PEC16-4215F-N0024", "1892676"). Preserve
   original casing and dashes.

8. "quantity" is the integer count of items (e.g. "5 PCS" → 5).

9. "description" is a short description if present (one line max), or null.

10. "currency_symbol" is one of "£", "$", "€" based on the document.

11. "supplier_name" is the company that issued the invoice.

12. "reference" is the invoice number, order number, or other primary
    reference identifier.

SANITY CHECK before returning: if printed_totals is present, then
   sum(quantity * unit_price_net for each line) + shipping_net
should be approximately equal to printed_totals.net (within 1% to allow for
rounding). If not, re-check whether you accidentally returned the LINE
TOTAL net rather than per-UNIT net for any line.

Return ONLY a JSON object with this exact structure (no markdown, no extra
text):
{
  "supplier_name": "string or null",
  "reference": "string or null",
  "currency_symbol": "string or null",
  "shipping_net": decimal_number,
  "shipping_vat_rate": decimal_number_or_null,
  "printed_totals": { "net": decimal, "vat": decimal, "gross": decimal } or null,
  "lines": [
    {
      "part_number": "string",
      "description": "string or null",
      "quantity": integer,
      "unit_price_net": decimal_number,
      "vat_rate": decimal_number_or_null
    }
  ]
}"""


def _call_llm(file_bytes: bytes) -> dict:
    """Send the PDF to OpenAI and return the parsed JSON dict.

    Uses the Responses API with an ``input_file`` content block so the model
    sees the rendered PDF (layout, tables, column alignment) rather than a
    flattened text approximation.
    """
    if not settings.OPENAI_API_KEY:
        raise AppError(500, "OPENAI_API_KEY is not configured")
    if not file_bytes:
        raise AppError(400, "Empty PDF file")

    pdf_b64 = base64.b64encode(file_bytes).decode("ascii")
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.responses.create(
        model=_MODEL,
        instructions=_SYSTEM_PROMPT,
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "Parse this invoice and return ONLY the JSON object "
                            "described in the system instructions. Remember: return "
                            "NET prices plus a per-line vat_rate; the backend will "
                            "compute gross."
                        ),
                    },
                    {
                        "type": "input_file",
                        "filename": "invoice.pdf",
                        "file_data": f"data:application/pdf;base64,{pdf_b64}",
                    },
                ],
            }
        ],
        text={"format": {"type": "json_object"}},
        temperature=0,
    )

    raw = (response.output_text or "").strip() or "{}"
    return json.loads(raw)


def _resolve_location(item_id: int) -> tuple[int | None, str | None]:
    """Return (location_id, location_code) for the stock row with the highest quantity."""
    try:
        resp = (
            supabase.table("stock")
            .select("location_id, quantity, location(code)")
            .eq("item_id", item_id)
            .gt("quantity", 0)
            .order("quantity", desc=True)
            .limit(1)
            .execute()
        )
        if resp.data:
            row = resp.data[0]
            loc = row.get("location") or {}
            return row["location_id"], loc.get("code")
    except Exception:
        pass
    return None, None


def _lookup_item_by_part_number(part_number: str, supplier_id: int | None) -> tuple[int | None, str | None]:
    """Resolve a printed part number to a DB item.

    Tries, in order:
    1. A user-recorded supplier-part-number alias (item_supplier.supplier_part_number).
       Highest signal: an actual human said "this supplier prints this string for this item".
    2. The historical dash-insensitive fuzzy match against item.item_id.
    """
    if not part_number:
        return None, None

    # 1. User-recorded supplier alias.
    if supplier_id is not None:
        item_id = _supplier_quote_repo.find_item_by_supplier_part_number(supplier_id, part_number)
        if item_id is not None:
            try:
                resp = supabase.table("item").select("id, item_id").eq("id", item_id).limit(1).execute()
                if resp.data:
                    return resp.data[0]["id"], resp.data[0]["item_id"]
            except Exception:
                pass

    # 2. Fuzzy match by item_id.
    try:
        pattern = dash_insensitive_pattern(part_number)
        resp = supabase.table("item").select("id, item_id").filter("item_id", "imatch", pattern).limit(5).execute()
        if resp.data:
            exact = next(
                (r for r in resp.data if r["item_id"].upper() == part_number.upper()),
                None,
            )
            best = exact or resp.data[0]
            return best["id"], best["item_id"]
    except Exception:
        pass
    return None, None


def _resolve_items(lines: list[dict], supplier_id: int | None = None) -> list[ResolvedLineItem]:
    resolved: list[ResolvedLineItem] = []

    for line in lines:
        part_number = line.get("part_number", "")
        matched_id, matched_name = _lookup_item_by_part_number(part_number, supplier_id)
        matched_location_id = None
        matched_location_code = None
        if matched_id is not None:
            matched_location_id, matched_location_code = _resolve_location(matched_id)

        net = _coerce_decimal(line.get("unit_price_net"))
        rate = _coerce_rate(line.get("vat_rate"))
        gross = _gross_from_net(net, rate) if net is not None else _coerce_decimal(line.get("unit_price"))

        resolved.append(
            ResolvedLineItem(
                part_number=part_number,
                description=line.get("description"),
                quantity=max(int(line.get("quantity", 1)), 1),
                unit_price=round(float(gross or 0.0), 4),
                unit_price_net=net,
                vat_rate=rate,
                matched_item_id=matched_id,
                matched_item_name=matched_name,
                matched_location_id=matched_location_id,
                matched_location_code=matched_location_code,
            )
        )

    return resolved


def _resolve_supplier(name: str | None) -> int | None:
    if not name:
        return None

    # 1. User-recorded alias takes priority — "Premier Farnell UK Ltd" → Farnell.
    try:
        alias = _alias_repo.find_by_alias(name)
        if alias:
            return alias["supplier_id"]
    except Exception:
        pass

    # 2. Fall back to fuzzy name match.
    try:
        resp = supabase.table("supplier").select("id, name").ilike("name", f"%{name}%").limit(5).execute()
        if resp.data:
            exact = next(
                (r for r in resp.data if r["name"].lower() == name.lower()),
                None,
            )
            return (exact or resp.data[0])["id"]
    except Exception:
        pass
    return None


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def parse_invoice_stream(file_bytes: bytes):
    """Yield SSE events: header → line (×N) → done, so the frontend can render progressively."""
    try:
        if not file_bytes:
            yield _sse("error", {"error": "Empty PDF file"})
            return

        parsed = _call_llm(file_bytes)

        supplier_name = parsed.get("supplier_name")
        matched_supplier_id = _resolve_supplier(supplier_name)

        lines = parsed.get("lines", [])

        shipping_net = _coerce_shipping_total(parsed.get("shipping_net"))
        shipping_vat_rate = _coerce_rate(parsed.get("shipping_vat_rate"))
        # Re-derive gross from net + rate so we never trust an LLM-grossed total.
        # Fall back to the legacy `shipping_total` field if the LLM only emitted
        # that (defensive — the new prompt does not request it).
        if parsed.get("shipping_net") is None and parsed.get("shipping_total") is not None:
            shipping_total = _coerce_shipping_total(parsed.get("shipping_total"))
        else:
            shipping_total = round(_gross_from_net(shipping_net, shipping_vat_rate), 4)

        printed_totals = _coerce_printed_totals(parsed.get("printed_totals"))

        yield _sse(
            "header",
            {
                "supplier_name": supplier_name,
                "matched_supplier_id": matched_supplier_id,
                "reference": parsed.get("reference"),
                "currency_symbol": parsed.get("currency_symbol"),
                "shipping_total": shipping_total,
                "shipping_net": shipping_net,
                "shipping_vat_rate": shipping_vat_rate,
                "printed_totals": printed_totals.model_dump() if printed_totals else None,
                "total_lines": len(lines),
            },
        )
        for line_data in lines:
            pn = line_data.get("part_number", "")
            mid, mname = _lookup_item_by_part_number(pn, matched_supplier_id)
            loc_id, loc_code = (None, None)
            if mid is not None:
                loc_id, loc_code = _resolve_location(mid)

            net = _coerce_decimal(line_data.get("unit_price_net"))
            rate = _coerce_rate(line_data.get("vat_rate"))
            if net is not None:
                gross = round(_gross_from_net(net, rate), 4)
            else:
                gross = round(float(line_data.get("unit_price", 0) or 0), 4)

            yield _sse(
                "line",
                {
                    "part_number": pn,
                    "description": line_data.get("description"),
                    "quantity": max(int(line_data.get("quantity", 1)), 1),
                    "unit_price": gross,
                    "unit_price_net": net,
                    "vat_rate": rate,
                    "matched_item_id": mid,
                    "matched_item_name": mname,
                    "matched_location_id": loc_id,
                    "matched_location_code": loc_code,
                },
            )

        yield _sse("done", {"total": len(lines)})

    except AppError as e:
        yield _sse("error", {"error": e.message})
    except Exception as e:
        yield _sse("error", {"error": str(e) or "Internal server error"})


def parse_invoice(file_bytes: bytes) -> ParseInvoiceResponse:
    if not file_bytes:
        raise AppError(400, "Empty PDF file")

    parsed = _call_llm(file_bytes)

    supplier_name = parsed.get("supplier_name")
    matched_supplier_id = _resolve_supplier(supplier_name)
    resolved_lines = _resolve_items(parsed.get("lines", []), matched_supplier_id)

    shipping_net = _coerce_shipping_total(parsed.get("shipping_net"))
    shipping_vat_rate = _coerce_rate(parsed.get("shipping_vat_rate"))
    if parsed.get("shipping_net") is None and parsed.get("shipping_total") is not None:
        shipping_total = _coerce_shipping_total(parsed.get("shipping_total"))
    else:
        shipping_total = round(_gross_from_net(shipping_net, shipping_vat_rate), 4)

    return ParseInvoiceResponse(
        supplier_name=supplier_name,
        matched_supplier_id=matched_supplier_id,
        reference=parsed.get("reference"),
        currency_symbol=parsed.get("currency_symbol"),
        shipping_total=shipping_total,
        shipping_net=shipping_net,
        shipping_vat_rate=shipping_vat_rate,
        printed_totals=_coerce_printed_totals(parsed.get("printed_totals")),
        lines=resolved_lines,
    )


def _coerce_shipping_total(raw) -> float:
    """Coerce an LLM shipping-total value to a non-negative rounded float."""
    if raw is None:
        return 0.0
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return 0.0
    if not (val == val) or val < 0:  # NaN or negative
        return 0.0
    return round(val, 4)


def _coerce_decimal(raw) -> float | None:
    """Coerce an LLM decimal value to a non-negative float, or None."""
    if raw is None:
        return None
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return None
    if not (val == val) or val < 0:  # NaN or negative
        return None
    return round(val, 4)


def _coerce_rate(raw) -> float | None:
    """Coerce a VAT-rate value to a non-negative float, or None.

    Accepts numeric values directly. A string like "20.00" is parsed; the
    "%" suffix is stripped if present. Negative or NaN inputs become None.
    """
    if raw is None:
        return None
    if isinstance(raw, str):
        raw = raw.strip().rstrip("%").strip()
        if not raw:
            return None
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return None
    if not (val == val) or val < 0:
        return None
    return round(val, 4)


def _gross_from_net(net: float | None, rate: float | None) -> float:
    """Return gross = net * (1 + rate/100). Treats None as 0."""
    safe_net = float(net) if net is not None else 0.0
    safe_rate = float(rate) if rate is not None else 0.0
    return round(safe_net * (1.0 + safe_rate / 100.0), 4)


def _coerce_printed_totals(raw) -> PrintedTotals | None:
    """Coerce an LLM `printed_totals` block into a validated model, or None."""
    if not isinstance(raw, dict):
        return None
    net = _coerce_decimal(raw.get("net"))
    vat = _coerce_decimal(raw.get("vat"))
    gross = _coerce_decimal(raw.get("gross"))
    if net is None or vat is None or gross is None:
        return None
    return PrintedTotals(net=net, vat=vat, gross=gross)
