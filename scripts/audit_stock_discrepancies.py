"""One-off audit: find every item where SUM(stock.quantity) != SUM(positive stock.quantity).

Such items render with a discrepancy on the Item Detail page because the header
sums all stock rows (including negatives) while the Locations panel filters to
quantity > 0. A divergence proves there is at least one negative-quantity stock
row, almost always caused by an oversell or by the eBay sync importing an order
into a location that had no on-hand.

Run from the backend root with the same environment as the API:

    cd nikkoe-backend
    python -m scripts.audit_stock_discrepancies

This is a read-only audit. It does not mutate any data.

Equivalent ad-hoc SQL (for use directly against Postgres):

    SELECT i.item_id, i.description,
           SUM(s.quantity)                                          AS total,
           SUM(CASE WHEN s.quantity > 0 THEN s.quantity ELSE 0 END) AS positive_sum,
           json_agg(json_build_object('location_id', s.location_id, 'qty', s.quantity)
                    ORDER BY s.location_id) AS rows
    FROM stock s JOIN item i ON i.id = s.item_id
    GROUP BY i.id, i.item_id, i.description
    HAVING SUM(s.quantity)
        <> SUM(CASE WHEN s.quantity > 0 THEN s.quantity ELSE 0 END);
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.dependencies import supabase  # noqa: E402

PAGE_SIZE = 1000


def fetch_all_stock() -> list[dict]:
    rows: list[dict] = []
    offset = 0
    while True:
        resp = (
            supabase.table("stock")
            .select("id, item_id, location_id, quantity")
            .order("id")
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
        )
        batch = resp.data or []
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return rows


def fetch_items(item_ids: list[int]) -> dict[int, dict]:
    out: dict[int, dict] = {}
    for i in range(0, len(item_ids), PAGE_SIZE):
        chunk = item_ids[i : i + PAGE_SIZE]
        resp = (
            supabase.table("item")
            .select("id, item_id, description")
            .in_("id", chunk)
            .execute()
        )
        for row in resp.data or []:
            out[row["id"]] = row
    return out


def fetch_locations(location_ids: list[int]) -> dict[int, dict]:
    out: dict[int, dict] = {}
    if not location_ids:
        return out
    for i in range(0, len(location_ids), PAGE_SIZE):
        chunk = location_ids[i : i + PAGE_SIZE]
        resp = supabase.table("location").select("id, code").in_("id", chunk).execute()
        for row in resp.data or []:
            out[row["id"]] = row
    return out


def main() -> int:
    print("Fetching all stock rows...")
    stock_rows = fetch_all_stock()
    print(f"  {len(stock_rows)} stock rows total")

    by_item: dict[int, list[dict]] = defaultdict(list)
    for row in stock_rows:
        by_item[row["item_id"]].append(row)

    discrepancies: list[dict] = []
    for item_id, rows in by_item.items():
        total = sum(int(r.get("quantity") or 0) for r in rows)
        positive_sum = sum(int(r.get("quantity") or 0) for r in rows if (r.get("quantity") or 0) > 0)
        if total != positive_sum:
            discrepancies.append(
                {
                    "item_pk": item_id,
                    "total": total,
                    "positive_sum": positive_sum,
                    "rows": rows,
                }
            )

    if not discrepancies:
        print("\nNo discrepancies found. Every item has total == sum of positive locations.")
        return 0

    items = fetch_items([d["item_pk"] for d in discrepancies])

    location_ids = sorted({r["location_id"] for d in discrepancies for r in d["rows"] if r.get("location_id")})
    locations = fetch_locations(location_ids)

    discrepancies.sort(key=lambda d: (d["positive_sum"] - d["total"]), reverse=True)

    print(f"\n{'=' * 100}")
    print(f"Found {len(discrepancies)} item(s) with Total != SUM(positive locations)")
    print(f"{'=' * 100}\n")

    header = (
        f"{'PART NUMBER':<24} {'TOTAL':>8} {'POS SUM':>8} {'DELTA':>8}  DESCRIPTION / OFFENDING ROWS"
    )
    print(header)
    print("-" * len(header))

    location_damage: dict[str, int] = defaultdict(int)

    for d in discrepancies:
        item = items.get(d["item_pk"], {})
        part_no = (item.get("item_id") or f"<pk={d['item_pk']}>")[:23]
        desc = (item.get("description") or "")[:60]
        delta = d["positive_sum"] - d["total"]
        print(f"{part_no:<24} {d['total']:>8} {d['positive_sum']:>8} {delta:>8}  {desc}")
        for r in sorted(d["rows"], key=lambda x: x.get("quantity") or 0):
            qty = int(r.get("quantity") or 0)
            loc_id = r.get("location_id")
            loc_code = (locations.get(loc_id, {}).get("code") if loc_id else None) or f"<id={loc_id}>"
            marker = "  !!" if qty < 0 else "    "
            print(f"{marker} {' ' * 19} loc={loc_code:<10}  qty={qty}")
            if qty < 0:
                location_damage[loc_code] += qty

    print(f"\n{'=' * 100}")
    print("Per-location damage (sum of negative quantities by location):")
    print(f"{'=' * 100}")
    if not location_damage:
        print("  (none)")
    else:
        for loc_code, dmg in sorted(location_damage.items(), key=lambda x: x[1]):
            print(f"  {loc_code:<20}  {dmg}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
