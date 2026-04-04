from app.dependencies import supabase


class CustomerRepository:
    def find_all(self, limit: int = 50, offset: int = 0) -> dict:
        response = (
            supabase.table("customer")
            .select("customer_id, name", count="exact")
            .order("name")
            .range(offset, offset + limit - 1)
            .execute()
        )
        return {"data": response.data or [], "total": response.count or 0}

    def create(self, data: dict) -> dict:
        response = (
            supabase.table("customer")
            .insert({"name": data["name"]})
            .select("customer_id, name")
            .execute()
        )
        return response.data[0]
