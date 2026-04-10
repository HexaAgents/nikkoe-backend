from app.dependencies import supabase


class SupplierQuoteRepository:
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
        existing = (
            supabase.table("item_supplier")
            .select("id")
            .eq("item_id", data["item_id"])
            .eq("supplier_id", data["supplier_id"])
            .maybe_single()
            .execute()
        )
        if existing.data:
            resp = supabase.table("item_supplier").update(data).eq("id", existing.data["id"]).execute()
            return resp.data[0]
        response = supabase.table("item_supplier").insert(data).execute()
        return response.data[0]

    def remove(self, id: int) -> None:
        supabase.table("item_supplier").delete().eq("id", id).execute()
