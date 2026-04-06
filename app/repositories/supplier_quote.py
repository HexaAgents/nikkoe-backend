from app.dependencies import supabase


class SupplierQuoteRepository:
    def find_by_item_id(self, item_id: int) -> list:
        response = (
            supabase.table("item_supplier")
            .select("*, supplier(name)")
            .eq("item_id", item_id)
            .order("date_time", desc=True)
            .execute()
        )
        return response.data or []

    def create(self, data: dict) -> dict:
        response = supabase.table("item_supplier").insert(data).execute()
        return response.data[0]

    def remove(self, id: int) -> None:
        supabase.table("item_supplier").delete().eq("id", id).execute()
