from app.dependencies import supabase


class ChannelRepository:
    def find_all(self, limit: int = 50, offset: int = 0) -> dict:
        response = (
            supabase.table("channels")
            .select("*", count="exact")
            .order("channel_name")
            .range(offset, offset + limit - 1)
            .execute()
        )
        return {"data": response.data or [], "total": response.count or 0}
