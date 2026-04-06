from app.dependencies import supabase

PAGE_SIZE = 1000


class LocationRepository:
    def find_all(self, limit: int = 5000, offset: int = 0) -> dict:
        all_data: list = []
        total = 0
        current_offset = offset
        remaining = limit

        while remaining > 0:
            batch = min(remaining, PAGE_SIZE)
            response = (
                supabase.table("location")
                .select("*", count="exact")
                .order("code")
                .range(current_offset, current_offset + batch - 1)
                .execute()
            )
            rows = response.data or []
            if total == 0:
                total = response.count or 0
            all_data.extend(rows)
            if len(rows) < batch:
                break
            current_offset += batch
            remaining -= batch

        return {"data": all_data, "total": total}

    def create(self, data: dict) -> dict:
        response = supabase.table("location").insert(data).execute()
        return response.data[0]

    def remove(self, id: int) -> None:
        supabase.table("location").delete().eq("id", id).execute()
