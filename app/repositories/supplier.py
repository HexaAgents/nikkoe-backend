from app.dependencies import supabase
from app.repositories.base import retry_transient


class SupplierRepository:
    @retry_transient()
    def find_all(self, limit: int = 50, offset: int = 0, search: str | None = None) -> dict:
        query = supabase.table("supplier").select("*", count="exact").order("name")
        if search:
            query = query.or_(
                f"name.ilike.%{search}%,email.ilike.%{search}%,address.ilike.%{search}%,phone.ilike.%{search}%"
            )
        response = query.range(offset, offset + limit - 1).execute()
        return {"data": response.data or [], "total": response.count or 0}

    def find_by_id(self, id: int) -> dict | None:
        response = supabase.table("supplier").select("*").eq("id", id).maybe_single().execute()
        return response.data

    def create(self, data: dict) -> dict:
        response = supabase.table("supplier").insert(data).execute()
        return response.data[0]

    def remove(self, id: int) -> None:
        supabase.table("supplier").delete().eq("id", id).execute()
