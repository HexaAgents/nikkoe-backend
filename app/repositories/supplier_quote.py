from app.dependencies import supabase


class SupplierQuoteRepository:
    def find_by_item_id(self, item_id: int) -> list:
        response = (
            supabase.table("Item_supplier")
            .select("*, Supplier(name)")
            .eq("item_id", item_id)
            .order("date_time", desc=True)
            .execute()
        )
        return response.data or []

    def create(self, data: dict) -> dict:
        response = supabase.table("Item_supplier").insert(data).select().single().execute()
        return response.data

    def remove(self, id: int) -> None:
        supabase.table("Item_supplier").delete().eq("id", id).execute()
