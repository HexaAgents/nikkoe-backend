from app.dependencies import supabase
from app.errors import AppError
from app.repositories.base import retry_transient


class SupplierAliasRepository:
    """Stores free-form supplier-name aliases that map to a canonical supplier.

    The invoice parser uses this table to short-circuit the fuzzy-name match
    once a user has confirmed that a particular invoice spelling
    (e.g. "Premier Farnell UK Ltd") refers to a known supplier
    (e.g. "Farnell")."""

    @retry_transient()
    def find_by_alias(self, alias: str) -> dict | None:
        if not alias:
            return None
        # Case-insensitive equality. We can't rely on the lower() unique index
        # for SELECT, so use ilike with no wildcards, which postgres can still
        # answer using the trigram/gin indexes if any.
        resp = (
            supabase.table("supplier_alias")
            .select("id, alias, supplier_id")
            .ilike("alias", alias)
            .limit(1)
            .execute()
        )
        rows = resp.data
        if not isinstance(rows, list) or not rows:
            return None
        row = rows[0]
        return row if isinstance(row, dict) else None

    def find_by_supplier(self, supplier_id: int) -> list[dict]:
        resp = (
            supabase.table("supplier_alias")
            .select("id, alias, supplier_id, created_at")
            .eq("supplier_id", supplier_id)
            .order("created_at", desc=True)
            .execute()
        )
        return resp.data or []

    def upsert(self, supplier_id: int, alias: str, *, created_by: int | None = None) -> dict:
        alias_clean = (alias or "").strip()
        if not alias_clean:
            raise AppError(400, "Alias cannot be empty")
        try:
            existing = self.find_by_alias(alias_clean)
            if existing:
                if existing["supplier_id"] == supplier_id:
                    return existing
                # Re-point an existing alias to a different supplier.
                resp = (
                    supabase.table("supplier_alias")
                    .update({"supplier_id": supplier_id})
                    .eq("id", existing["id"])
                    .execute()
                )
                return resp.data[0]
            payload: dict = {"alias": alias_clean, "supplier_id": supplier_id}
            if created_by is not None:
                payload["created_by"] = created_by
            resp = supabase.table("supplier_alias").insert(payload).execute()
            return resp.data[0]
        except AppError:
            raise
        except Exception as exc:
            raise AppError(400, f"Failed to save supplier alias: {exc}")

    def remove(self, alias_id: int) -> None:
        supabase.table("supplier_alias").delete().eq("id", alias_id).execute()
