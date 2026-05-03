"""Reconcile hidden negative stock rows with an auditable correction workflow.

Default mode is a dry run:

    cd nikkoe-backend
    python scripts/reconcile_stock_discrepancies.py --dry-run

Target one item:

    python scripts/reconcile_stock_discrepancies.py --item TC514400Z-80

Apply only safe placeholder offsets:

    python scripts/reconcile_stock_discrepancies.py --apply --batch-note "Reconcile placeholder negatives"

The apply path does not update stock directly from Python. It calls the
apply_stock_adjustment_batch Postgres RPC, which locks rows, verifies expected
quantities, applies deltas, and writes stock_adjustment audit rows.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.dependencies import supabase  # noqa: E402

PAGE_SIZE = 1000
DEFAULT_PLACEHOLDER_CODES = {"0", "PegNotIdentified"}
AUTO_OFFSET_PLACEHOLDER = "AUTO_OFFSET_PLACEHOLDER"
MANUAL_NO_POSITIVE_STOCK = "MANUAL_NO_POSITIVE_STOCK"
MANUAL_INSUFFICIENT_POSITIVE_STOCK = "MANUAL_INSUFFICIENT_POSITIVE_STOCK"
MANUAL_REAL_NEGATIVE_LOCATION = "MANUAL_REAL_NEGATIVE_LOCATION"
MANUAL_NEGATIVE_TOTAL = "MANUAL_NEGATIVE_TOTAL"


@dataclass(frozen=True)
class StockRow:
    id: int
    item_id: int
    location_id: int
    quantity: int
    location_code: str


@dataclass(frozen=True)
class ItemRow:
    id: int
    item_id: str
    description: str | None = None


@dataclass(frozen=True)
class Adjustment:
    stock_id: int
    item_id: int
    location_id: int
    location_code: str
    quantity_before: int
    quantity_delta: int
    reason: str
    source: str = "MISMATCH_RECONCILIATION"

    @property
    def quantity_after(self) -> int:
        return self.quantity_before + self.quantity_delta

    def rpc_payload(self) -> dict:
        return {
            "stock_id": self.stock_id,
            "item_id": self.item_id,
            "location_id": self.location_id,
            "quantity_before": self.quantity_before,
            "quantity_delta": self.quantity_delta,
            "reason": self.reason,
            "source": self.source,
        }


@dataclass
class ReconciliationResult:
    classification: str
    item: ItemRow
    rows: list[StockRow]
    total: int
    positive_total: int
    adjustments: list[Adjustment] = field(default_factory=list)
    message: str = ""

    @property
    def negative_total(self) -> int:
        return sum(row.quantity for row in self.rows if row.quantity < 0)


def is_placeholder_location(code: str, placeholder_codes: set[str]) -> bool:
    return code in placeholder_codes


def classify_item(
    item: ItemRow,
    rows: list[StockRow],
    *,
    placeholder_codes: set[str] | None = None,
) -> ReconciliationResult | None:
    placeholder_codes = placeholder_codes or DEFAULT_PLACEHOLDER_CODES
    total = sum(row.quantity for row in rows)
    positive_total = sum(row.quantity for row in rows if row.quantity > 0)
    negative_rows = [row for row in rows if row.quantity < 0]

    if not negative_rows:
        return None

    if total < 0:
        return ReconciliationResult(
            classification=MANUAL_NEGATIVE_TOTAL,
            item=item,
            rows=rows,
            total=total,
            positive_total=positive_total,
            message="Item net total is negative; requires manual inventory decision.",
        )

    if any(not is_placeholder_location(row.location_code, placeholder_codes) for row in negative_rows):
        return ReconciliationResult(
            classification=MANUAL_REAL_NEGATIVE_LOCATION,
            item=item,
            rows=rows,
            total=total,
            positive_total=positive_total,
            message="At least one negative row is in a real location.",
        )

    positive_real_rows = [
        row
        for row in rows
        if row.quantity > 0 and not is_placeholder_location(row.location_code, placeholder_codes)
    ]
    positive_real_total = sum(row.quantity for row in positive_real_rows)
    debt = -sum(row.quantity for row in negative_rows)

    if not positive_real_rows:
        return ReconciliationResult(
            classification=MANUAL_NO_POSITIVE_STOCK,
            item=item,
            rows=rows,
            total=total,
            positive_total=positive_total,
            message="No positive real-location stock exists to offset placeholder negatives.",
        )

    if positive_real_total < debt:
        return ReconciliationResult(
            classification=MANUAL_INSUFFICIENT_POSITIVE_STOCK,
            item=item,
            rows=rows,
            total=total,
            positive_total=positive_total,
            message=f"Positive real-location stock ({positive_real_total}) is less than placeholder debt ({debt}).",
        )

    adjustments: list[Adjustment] = []
    remaining_debt = debt
    reason = (
        "Reconcile hidden negative stock: offset placeholder location debt "
        f"against real locations; preserved item total {total}"
    )

    for row in negative_rows:
        adjustments.append(
            Adjustment(
                stock_id=row.id,
                item_id=row.item_id,
                location_id=row.location_id,
                location_code=row.location_code,
                quantity_before=row.quantity,
                quantity_delta=-row.quantity,
                reason=reason,
            )
        )

    for row in sorted(positive_real_rows, key=lambda r: r.quantity, reverse=True):
        if remaining_debt == 0:
            break
        take = min(row.quantity, remaining_debt)
        adjustments.append(
            Adjustment(
                stock_id=row.id,
                item_id=row.item_id,
                location_id=row.location_id,
                location_code=row.location_code,
                quantity_before=row.quantity,
                quantity_delta=-take,
                reason=reason,
            )
        )
        remaining_debt -= take

    return ReconciliationResult(
        classification=AUTO_OFFSET_PLACEHOLDER,
        item=item,
        rows=rows,
        total=total,
        positive_total=positive_total,
        adjustments=adjustments,
        message="Safe placeholder offset; item total is preserved.",
    )


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


def fetch_items(item_ids: Iterable[int]) -> dict[int, ItemRow]:
    ids = sorted(set(item_ids))
    out: dict[int, ItemRow] = {}
    for i in range(0, len(ids), PAGE_SIZE):
        chunk = ids[i : i + PAGE_SIZE]
        resp = supabase.table("item").select("id, item_id, description").in_("id", chunk).execute()
        for row in resp.data or []:
            out[row["id"]] = ItemRow(
                id=row["id"],
                item_id=row.get("item_id") or f"<pk={row['id']}>",
                description=row.get("description"),
            )
    return out


def fetch_locations(location_ids: Iterable[int]) -> dict[int, str]:
    ids = sorted(set(location_ids))
    out: dict[int, str] = {}
    for i in range(0, len(ids), PAGE_SIZE):
        chunk = ids[i : i + PAGE_SIZE]
        resp = supabase.table("location").select("id, code").in_("id", chunk).execute()
        for row in resp.data or []:
            out[row["id"]] = row.get("code") or f"<id={row['id']}>"
    return out


def resolve_item_filter(part_number: str) -> int | None:
    resp = supabase.table("item").select("id").eq("item_id", part_number).limit(1).execute()
    if not resp.data:
        return None
    return resp.data[0]["id"]


def build_results(
    stock_rows: list[dict],
    items: dict[int, ItemRow],
    locations: dict[int, str],
    *,
    placeholder_codes: set[str],
) -> list[ReconciliationResult]:
    by_item: dict[int, list[StockRow]] = defaultdict(list)
    for row in stock_rows:
        item_id = row["item_id"]
        location_id = row["location_id"]
        by_item[item_id].append(
            StockRow(
                id=row["id"],
                item_id=item_id,
                location_id=location_id,
                quantity=int(row.get("quantity") or 0),
                location_code=locations.get(location_id, f"<id={location_id}>"),
            )
        )

    results: list[ReconciliationResult] = []
    for item_pk, rows in by_item.items():
        item = items.get(item_pk) or ItemRow(id=item_pk, item_id=f"<pk={item_pk}>")
        result = classify_item(item, rows, placeholder_codes=placeholder_codes)
        if result is not None:
            results.append(result)

    return sorted(results, key=lambda r: (r.classification != AUTO_OFFSET_PLACEHOLDER, r.item.item_id))


def write_csv(path: Path, results: list[ReconciliationResult]) -> None:
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "classification",
                "part_number",
                "description",
                "total",
                "positive_total",
                "negative_total",
                "stock_id",
                "location",
                "quantity_before",
                "quantity_delta",
                "quantity_after",
                "message",
            ],
        )
        writer.writeheader()
        for result in results:
            if result.adjustments:
                for adj in result.adjustments:
                    writer.writerow(
                        {
                            "classification": result.classification,
                            "part_number": result.item.item_id,
                            "description": result.item.description or "",
                            "total": result.total,
                            "positive_total": result.positive_total,
                            "negative_total": result.negative_total,
                            "stock_id": adj.stock_id,
                            "location": adj.location_code,
                            "quantity_before": adj.quantity_before,
                            "quantity_delta": adj.quantity_delta,
                            "quantity_after": adj.quantity_after,
                            "message": result.message,
                        }
                    )
            else:
                for row in sorted(result.rows, key=lambda r: r.quantity):
                    if row.quantity >= 0:
                        continue
                    writer.writerow(
                        {
                            "classification": result.classification,
                            "part_number": result.item.item_id,
                            "description": result.item.description or "",
                            "total": result.total,
                            "positive_total": result.positive_total,
                            "negative_total": result.negative_total,
                            "stock_id": row.id,
                            "location": row.location_code,
                            "quantity_before": row.quantity,
                            "quantity_delta": "",
                            "quantity_after": "",
                            "message": result.message,
                        }
                    )


def print_report(results: list[ReconciliationResult]) -> None:
    counts = Counter(result.classification for result in results)
    auto_results = [result for result in results if result.classification == AUTO_OFFSET_PLACEHOLDER]
    manual_results = [result for result in results if result.classification != AUTO_OFFSET_PLACEHOLDER]
    adjustments = [adj for result in auto_results for adj in result.adjustments]

    print("\nStock reconciliation dry-run")
    print("=" * 100)
    print(f"Items with negative rows:        {len(results)}")
    print(f"Auto-fixable placeholder items: {len(auto_results)}")
    print(f"Manual-review items:            {len(manual_results)}")
    print(f"Adjustment rows proposed:       {len(adjustments)}")
    print(f"Net quantity delta proposed:    {sum(adj.quantity_delta for adj in adjustments)}")
    print("\nClassification counts:")
    for classification, count in sorted(counts.items()):
        print(f"  {classification:<36} {count}")

    print("\nTop proposed auto-fixes:")
    for result in auto_results[:20]:
        desc = (result.item.description or "")[:50]
        deltas = ", ".join(
            f"{adj.location_code}:{adj.quantity_before}->{adj.quantity_after}" for adj in result.adjustments
        )
        print(f"  {result.item.item_id:<24} total={result.total:<6} {desc} | {deltas}")

    print("\nManual-review examples:")
    for result in manual_results[:20]:
        negs = ", ".join(f"{row.location_code}:{row.quantity}" for row in result.rows if row.quantity < 0)
        print(f"  {result.item.item_id:<24} {result.classification:<36} total={result.total:<6} {negs}")


def apply_adjustments(results: list[ReconciliationResult], *, batch_note: str, created_by: int | None) -> dict:
    auto_results = [result for result in results if result.classification == AUTO_OFFSET_PLACEHOLDER]
    adjustments = [adj.rpc_payload() for result in auto_results for adj in result.adjustments]
    if not adjustments:
        return {"batch_id": None, "adjusted_items": 0, "adjusted_rows": 0, "total_delta": 0}

    metadata = {
        "script": "reconcile_stock_discrepancies.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "auto_item_count": len(auto_results),
        "manual_item_count": len(results) - len(auto_results),
        "classifications": dict(Counter(result.classification for result in results)),
    }
    resp = (
        supabase.rpc(
            "apply_stock_adjustment_batch",
            {
                "p_reason": batch_note,
                "p_adjustments": adjustments,
                "p_created_by": created_by,
                "p_metadata": metadata,
            },
        )
        .execute()
    )
    return resp.data or {}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dry-run or apply safe stock mismatch reconciliation.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Compute proposed corrections without applying them (default).")
    mode.add_argument("--apply", action="store_true", help="Apply AUTO_OFFSET_PLACEHOLDER corrections via RPC.")
    parser.add_argument("--item", help="Limit to one part number, e.g. TC514400Z-80.")
    parser.add_argument("--export-csv", type=Path, help="Write detailed proposed/manual rows to CSV.")
    parser.add_argument("--batch-note", help="Reason saved on the adjustment batch when using --apply.")
    parser.add_argument("--created-by", type=int, help="Optional user.id to store on stock_adjustment_batch.created_by.")
    parser.add_argument(
        "--placeholder-code",
        action="append",
        dest="placeholder_codes",
        help="Location code treated as a placeholder. Can be repeated. Defaults to 0 and PegNotIdentified.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    placeholder_codes = set(args.placeholder_codes or DEFAULT_PLACEHOLDER_CODES)

    if args.apply and not args.batch_note:
        print("--apply requires --batch-note", file=sys.stderr)
        return 2

    stock_rows = fetch_all_stock()
    if args.item:
        item_pk = resolve_item_filter(args.item)
        if item_pk is None:
            print(f"Item {args.item!r} not found", file=sys.stderr)
            return 1
        stock_rows = [row for row in stock_rows if row["item_id"] == item_pk]

    item_ids = [row["item_id"] for row in stock_rows]
    location_ids = [row["location_id"] for row in stock_rows]
    items = fetch_items(item_ids)
    locations = fetch_locations(location_ids)
    results = build_results(stock_rows, items, locations, placeholder_codes=placeholder_codes)

    print_report(results)

    if args.export_csv:
        write_csv(args.export_csv, results)
        print(f"\nCSV exported to {args.export_csv}")

    if args.apply:
        result = apply_adjustments(results, batch_note=args.batch_note, created_by=args.created_by)
        print("\nApplied adjustment batch:")
        print(json.dumps(result, indent=2, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
