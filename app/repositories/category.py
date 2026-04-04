from app.dependencies import supabase


class CategoryRepository:
    def find_all(self, limit: int = 50, offset: int = 0) -> dict:
        response = (
            supabase.table("categories")
            .select("*", count="exact")
            .order("name")
            .range(offset, offset + limit - 1)
            .execute()
        )
        return {"data": response.data or [], "total": response.count or 0}

    def create(self, data: dict) -> dict:
        response = (
            supabase.table("categories").insert(data).select().single().execute()
        )
        return response.data

    def remove(self, id: str) -> None:
        supabase.table("categories").delete().eq("category_id", id).execute()
