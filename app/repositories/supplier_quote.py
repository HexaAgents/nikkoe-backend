from app.dependencies import supabase
from app.errors import AppError
from app.repositories.base import retry_transient


class SupplierQuoteRepository:
    @retry_transient()
    def find_by_item_id(self, item_id: int) -> list:
        response = (
            supabase.table("item_supplier")
            .select("*, supplier(name), currency(name)")
            .eq("item_id", item_id)
            .order("date_time", desc=True)
            .execute()
        )
        return response.data or []

    def create(self, data: dict) -> dict:
        try:
            response = supabase.table("item_supplier").upsert(data, on_conflict="item_id,supplier_id").execute()
            return response.data[0]
        except AppError:
            raise
        except Exception as exc:
            raise AppError(400, f"Failed to save supplier quote: {exc}")

    def remove(self, id: int) -> None:
        supabase.table("item_supplier").delete().eq("id", id).execute()

    @retry_transient()
    def find_item_by_supplier_part_number(self, supplier_id: int, supplier_part_number: str) -> int | None:
        """Return the item_id this supplier maps the given printed part number
        to, or None when no such mapping has been recorded."""
        if not supplier_part_number:
            return None
        try:
            resp = (
                supabase.table("item_supplier")
                .select("item_id")
                .eq("supplier_id", supplier_id)
                # Case-insensitive exact match — invoices are noisy with casing.
                .ilike("supplier_part_number", supplier_part_number)
                .limit(1)
                .execute()
            )
            rows = resp.data
            if not isinstance(rows, list) or not rows:
                return None
            row = rows[0]
            if not isinstance(row, dict):
                return None
            value = row.get("item_id")
            return value if isinstance(value, int) else None
        except Exception:
            return None

    def set_supplier_part_number(self, item_id: int, supplier_id: int, supplier_part_number: str) -> dict:
        """Record that *supplier* prints *supplier_part_number* for *item*.

        Upserts on the existing (item_id, supplier_id) row so this never
        creates duplicate rows; the supplier's quote/cost data, if any,
        survives untouched."""
        clean = (supplier_part_number or "").strip()
        if not clean:
            raise AppError(400, "supplier_part_number cannot be empty")
        try:
            payload = {
                "item_id": item_id,
                "supplier_id": supplier_id,
                "supplier_part_number": clean,
            }
            response = supabase.table("item_supplier").upsert(payload, on_conflict="item_id,supplier_id").execute()
            return response.data[0]
        except AppError:
            raise
        except Exception as exc:
            raise AppError(400, f"Failed to save supplier part-number mapping: {exc}")
