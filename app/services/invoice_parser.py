from __future__ import annotations

import io
import json

import pdfplumber
from openai import OpenAI

from app.config import settings
from app.dependencies import supabase
from app.errors import AppError
from app.repositories.base import dash_insensitive_pattern
from app.schemas import ParseInvoiceResponse, ResolvedLineItem

_SYSTEM_PROMPT = """\
You are an invoice parser for an electronics parts distributor.
Extract structured data from the invoice text provided by the user.

Rules:
1. Only extract physical product/component line items.
2. SKIP shipping, transport, handling, postage (P&P), bank charges, and insurance lines.
3. "part_number" must be the manufacturer or distributor part number exactly as printed \
(e.g. "SN74LS153N", "PEC16-4215F-N0024", "1892676"). Preserve original casing and dashes.
4. "quantity" is the integer count of items (e.g. "5 PCS" → 5).
5. "unit_price" is the price PER SINGLE UNIT as a decimal number.
   - If the invoice shows a bulk price like "8,73/10 PCS", compute per-unit: 8.73 / 10 = 0.873
   - Convert European comma decimals to dots: "1,95" → 1.95
   - Use the net/pre-tax price when both net and gross are shown.
6. "description" is a short description if present (one line max), or null.
7. "currency_symbol" is one of "£", "$", "€" based on the document.
8. "supplier_name" is the company that issued the invoice.
9. "reference" is the invoice number, order number, or other primary reference identifier.

Return ONLY a JSON object with this exact structure (no markdown, no extra text):
{
  "supplier_name": "string or null",
  "reference": "string or null",
  "currency_symbol": "string or null",
  "lines": [
    {
      "part_number": "string",
      "description": "string or null",
      "quantity": integer,
      "unit_price": decimal_number
    }
  ]
}"""


def extract_text_from_pdf(file_bytes: bytes) -> str:
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]
    return "\n\n".join(pages)


def _call_llm(text: str) -> dict:
    if not settings.OPENAI_API_KEY:
        raise AppError(500, "OPENAI_API_KEY is not configured")

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"Parse this invoice:\n\n{text}"},
        ],
        temperature=0,
    )

    raw = response.choices[0].message.content or "{}"
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


def _resolve_items(lines: list[dict]) -> list[ResolvedLineItem]:
    resolved: list[ResolvedLineItem] = []

    for line in lines:
        part_number = line.get("part_number", "")
        matched_id = None
        matched_name = None
        matched_location_id = None
        matched_location_code = None

        if part_number:
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
                    matched_id = best["id"]
                    matched_name = best["item_id"]
                    matched_location_id, matched_location_code = _resolve_location(matched_id)
            except Exception:
                pass

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
        text = extract_text_from_pdf(file_bytes)
        if not text.strip():
            yield _sse("error", {"error": "Could not extract any text from the PDF"})
            return

        parsed = _call_llm(text)

        supplier_name = parsed.get("supplier_name")
        matched_supplier_id = _resolve_supplier(supplier_name)

        lines = parsed.get("lines", [])

        yield _sse(
            "header",
            {
                "supplier_name": supplier_name,
                "matched_supplier_id": matched_supplier_id,
                "reference": parsed.get("reference"),
                "currency_symbol": parsed.get("currency_symbol"),
                "total_lines": len(lines),
            },
        )
        for line_data in lines:
            pn = line_data.get("part_number", "")
            mid, mname, loc_id, loc_code = None, None, None, None

            if pn:
                try:
                    pattern = dash_insensitive_pattern(pn)
                    resp = (
                        supabase.table("item")
                        .select("id, item_id")
                        .filter("item_id", "imatch", pattern)
                        .limit(5)
                        .execute()
                    )
                    if resp.data:
                        exact = next((r for r in resp.data if r["item_id"].upper() == pn.upper()), None)
                        best = exact or resp.data[0]
                        mid = best["id"]
                        mname = best["item_id"]
                        loc_id, loc_code = _resolve_location(mid)
                except Exception:
                    pass

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
    text = extract_text_from_pdf(file_bytes)
    if not text.strip():
        raise AppError(400, "Could not extract any text from the PDF")

    parsed = _call_llm(text)

    supplier_name = parsed.get("supplier_name")
    matched_supplier_id = _resolve_supplier(supplier_name)
    resolved_lines = _resolve_items(parsed.get("lines", []))

    return ParseInvoiceResponse(
        supplier_name=supplier_name,
        matched_supplier_id=matched_supplier_id,
        reference=parsed.get("reference"),
        currency_symbol=parsed.get("currency_symbol"),
        lines=resolved_lines,
    )
