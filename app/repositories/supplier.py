from app.dependencies import supabase


class SupplierRepository:
    def find_all(self, limit: int = 50, offset: int = 0) -> dict:
        response = (
            supabase.table("suppliers")
            .select("*", count="exact")
            .order("supplier_name")
            .range(offset, offset + limit - 1)
            .execute()
        )
        return {"data": response.data or [], "total": response.count or 0}

    def create(self, data: dict) -> dict:
        response = supabase.table("suppliers").insert(data).select().single().execute()
        return response.data

    def remove(self, id: str) -> None:
        supabase.table("suppliers").delete().eq("supplier_id", id).execute()
