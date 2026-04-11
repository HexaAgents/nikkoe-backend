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
            existing = (
                supabase.table("item_supplier")
                .select("id")
                .eq("item_id", data["item_id"])
                .eq("supplier_id", data["supplier_id"])
                .limit(1)
                .execute()
            )
            if existing.data:
                row_id = existing.data[0]["id"]
                update_data = {k: v for k, v in data.items() if k not in ("item_id", "supplier_id")}
                resp = supabase.table("item_supplier").update(update_data).eq("id", row_id).execute()
                return resp.data[0]
            response = supabase.table("item_supplier").insert(data).execute()
            return response.data[0]
        except AppError:
            raise
        except Exception as exc:
            raise AppError(400, f"Failed to save supplier quote: {exc}")

    def remove(self, id: int) -> None:
        supabase.table("item_supplier").delete().eq("id", id).execute()
