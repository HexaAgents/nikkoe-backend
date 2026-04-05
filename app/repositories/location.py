from app.dependencies import supabase


class LocationRepository:
    def find_all(self, limit: int = 50, offset: int = 0) -> dict:
        response = (
            supabase.table("Location")
            .select("*", count="exact")
            .order("code")
            .range(offset, offset + limit - 1)
            .execute()
        )
        return {"data": response.data or [], "total": response.count or 0}

    def create(self, data: dict) -> dict:
        response = supabase.table("Location").insert(data).execute()
        return response.data[0]

    def remove(self, id: int) -> None:
        supabase.table("Location").delete().eq("id", id).execute()
