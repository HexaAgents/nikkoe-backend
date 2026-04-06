from app.dependencies import supabase


class CategoryRepository:
    def find_all(self, limit: int = 50, offset: int = 0) -> dict:
        response = (
            supabase.table("category")
            .select("*", count="exact")
            .order("name")
            .range(offset, offset + limit - 1)
            .execute()
        )
        return {"data": response.data or [], "total": response.count or 0}

    def create(self, data: dict) -> dict:
        response = supabase.table("category").insert(data).execute()
        return response.data[0]

    def remove(self, id: int) -> None:
        supabase.table("category").delete().eq("id", id).execute()
