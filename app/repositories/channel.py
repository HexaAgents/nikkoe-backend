from app.dependencies import supabase


class ChannelRepository:
    def find_all(self, limit: int = 50, offset: int = 0) -> dict:
        response = (
            supabase.table("Channel")
            .select("*", count="exact")
            .order("name")
            .range(offset, offset + limit - 1)
            .execute()
        )
        return {"data": response.data or [], "total": response.count or 0}
