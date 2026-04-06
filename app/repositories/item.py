from app.dependencies import supabase
from app.repositories.base import batch_load

PAGE_SIZE = 1000


class ItemRepository:
    def find_all(self, limit: int = 1000, offset: int = 0) -> dict:
        response = (
            supabase.table("item")
            .select("*, category(name), stock(quantity)", count="exact")
            .order("item_id")
            .range(offset, offset + min(limit, PAGE_SIZE) - 1)
            .execute()
        )
        items = response.data or []
        total = response.count or 0

        for item in items:
            item["categories"] = item.pop("category", None)
            stock_rows = item.pop("stock", [])
            item["total_quantity"] = sum(s.get("quantity", 0) for s in stock_rows)

        return {"data": items, "total": total}

    def find_by_id(self, id: int) -> dict | None:
        response = supabase.table("item").select("*, category(name)").eq("id", id).maybe_single().execute()
        if response.data:
            response.data["categories"] = response.data.pop("category", None)
        return response.data

    def create(self, data: dict) -> dict:
        response = supabase.table("item").insert(data).execute()
        return response.data[0]

    def update(self, id: int, data: dict) -> dict:
        response = supabase.table("item").update(data).eq("id", id).execute()
        return response.data[0]

    def remove(self, id: int) -> None:
        supabase.table("item").delete().eq("id", id).execute()
