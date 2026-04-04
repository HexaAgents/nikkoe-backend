from app.dependencies import supabase


class LocationRepository:
    def find_all(self, limit: int = 50, offset: int = 0) -> dict:
        response = (
            supabase.table("locations")
            .select("*", count="exact")
            .order("location_code")
            .range(offset, offset + limit - 1)
            .execute()
        )
        return {"data": response.data or [], "total": response.count or 0}

    def create(self, data: dict) -> dict:
        response = supabase.table("locations").insert(data).select().single().execute()
        return response.data

    def remove(self, id: str) -> None:
        supabase.table("locations").delete().eq("location_id", id).execute()
