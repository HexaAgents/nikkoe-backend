from app.dependencies import supabase


class SupplierQuoteRepository:
    def find_by_item_id(self, item_id: str) -> list:
        response = (
            supabase.table("supplier_quotes")
            .select("*, suppliers(supplier_name)")
            .eq("item_id", item_id)
            .order("quoted_at", desc=True)
            .execute()
        )
        return response.data or []

    def create(self, data: dict) -> dict:
        response = (
            supabase.table("supplier_quotes").insert(data).select().single().execute()
        )
        return response.data

    def remove(self, id: str) -> None:
        supabase.table("supplier_quotes").delete().eq("quote_id", id).execute()
