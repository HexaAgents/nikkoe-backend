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
from app.schemas import ParseInvoiceResponse, ResolvedLineItem

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

PRICES MUST BE GROSS (VAT-inclusive). The downstream system stores these
values as the per-unit stock cost, so they must already include any sales
tax / VAT printed on the invoice.

Rules:

1. "lines" must contain ONLY physical product / component line items. DO NOT
   put shipping, transport, carriage, postage (P&P), delivery, bank charges,
   handling or insurance rows into "lines".

2. "unit_price" is the GROSS (VAT-inclusive) price per single unit, as a
   decimal number in the invoice currency.
   - If the invoice prints both net and gross per unit, use the gross.
   - If the invoice prints only a net price plus a VAT rate column (e.g.
     Farnell prints `Net Price 0.9450  Vat Rate 20.00`), compute
     gross = net * (1 + rate/100). Round to 4 decimal places.
   - If the invoice has zero VAT (rate is 0% or the invoice has no VAT
     section at all — e.g. proforma invoices from non-VAT-registered
     overseas suppliers), gross == net; just return the printed price.
   - If the invoice shows a bulk price like "8,73/10 PCS", compute per-unit:
     8.73 / 10 = 0.873 (then apply VAT if applicable).
   - Convert European comma decimals to dots: "1,95" → 1.95.

3. "shipping_total" is the GROSS (VAT-inclusive) sum of all shipping /
   freight / carriage / postage (P&P) / delivery charges, as a single
   decimal number in the invoice currency. Apply the same gross-up rule as
   for unit_price. Return 0 if the invoice shows no shipping charge.
   - CRITICAL: A label like "P&P Charge", "Shipping", "Carriage", or
     "Delivery" with NO numeric value next to it means there is NO shipping
     charge — return 0. Do NOT borrow a number from a different column
     (VAT rate %, goods subtotal, VAT amount, etc.) just because a shipping
     label exists on the page.
   - A "Vat Rate" of "20.00" (a percentage) is NEVER the shipping amount.

4. "part_number" must be the manufacturer or distributor part number exactly
   as printed (e.g. "SN74LS153N", "PEC16-4215F-N0024", "1892676"). Preserve
   original casing and dashes.

5. "quantity" is the integer count of items (e.g. "5 PCS" → 5).

6. "description" is a short description if present (one line max), or null.

7. "currency_symbol" is one of "£", "$", "€" based on the document.

8. "supplier_name" is the company that issued the invoice.

9. "reference" is the invoice number, order number, or other primary
   reference identifier.

SANITY CHECK before returning: if the invoice prints an explicit
"Invoice Total" / "Grand Total" / "Total Due" / "TOTAL" line, then
   shipping_total + sum(quantity * unit_price for each line)
should be approximately equal to that printed total (within 1% to allow for
rounding when grossing-up per-unit). If you cannot make the totals balance,
double-check whether you accidentally returned net prices — if so, multiply
each unit_price (and shipping_total) by (1 + vat_rate/100).

Return ONLY a JSON object with this exact structure (no markdown, no extra
text):
{
  "supplier_name": "string or null",
  "reference": "string or null",
  "currency_symbol": "string or null",
  "shipping_total": decimal_number,
  "lines": [
    {
      "part_number": "string",
      "description": "string or null",
      "quantity": integer,
      "unit_price": decimal_number
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
                            "described in the system instructions. Remember: prices "
                            "must be GROSS (VAT-inclusive)."
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
                resp = (
                    supabase.table("item")
                    .select("id, item_id")
                    .eq("id", item_id)
                    .limit(1)
                    .execute()
                )
                if resp.data:
                    return resp.data[0]["id"], resp.data[0]["item_id"]
            except Exception:
                pass

    # 2. Fuzzy match by item_id.
    try:
        pattern = dash_insensitive_pattern(part_number)
        resp = (
            supabase.table("item").select("id, item_id").filter("item_id", "imatch", pattern).limit(5).execute()
        )
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

        resolved.append(
            ResolvedLineItem(
                part_number=part_number,
                description=line.get("description"),
                quantity=max(int(line.get("quantity", 1)), 1),
                unit_price=round(float(line.get("unit_price", 0)), 4),
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
        shipping_total = _coerce_shipping_total(parsed.get("shipping_total"))

        yield _sse(
            "header",
            {
                "supplier_name": supplier_name,
                "matched_supplier_id": matched_supplier_id,
                "reference": parsed.get("reference"),
                "currency_symbol": parsed.get("currency_symbol"),
                "shipping_total": shipping_total,
                "total_lines": len(lines),
            },
        )
        for line_data in lines:
            pn = line_data.get("part_number", "")
            mid, mname = _lookup_item_by_part_number(pn, matched_supplier_id)
            loc_id, loc_code = (None, None)
            if mid is not None:
                loc_id, loc_code = _resolve_location(mid)

            yield _sse(
                "line",
                {
                    "part_number": pn,
                    "description": line_data.get("description"),
                    "quantity": max(int(line_data.get("quantity", 1)), 1),
                    "unit_price": round(float(line_data.get("unit_price", 0)), 4),
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

    return ParseInvoiceResponse(
        supplier_name=supplier_name,
        matched_supplier_id=matched_supplier_id,
        reference=parsed.get("reference"),
        currency_symbol=parsed.get("currency_symbol"),
        shipping_total=_coerce_shipping_total(parsed.get("shipping_total")),
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
