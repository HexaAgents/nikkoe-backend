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
        categories = response.data or []

        item_response = (
            supabase.table("item").select("category_id, stock(quantity)").not_.is_("category_id", "null").execute()
        )
        stats: dict[int, dict] = {}
        for item in item_response.data or []:
            cat_id = item["category_id"]
            if cat_id not in stats:
                stats[cat_id] = {"item_count": 0, "total_quantity": 0}
            stats[cat_id]["item_count"] += 1
            for s in item.get("stock") or []:
                stats[cat_id]["total_quantity"] += s.get("quantity", 0)

        for cat in categories:
            cat_stats = stats.get(cat["id"], {"item_count": 0, "total_quantity": 0})
            cat["item_count"] = cat_stats["item_count"]
            cat["total_quantity"] = cat_stats["total_quantity"]

        return {"data": categories, "total": response.count or 0}

    def find_by_id(self, id: int) -> dict | None:
        response = supabase.table("category").select("*").eq("id", id).maybe_single().execute()
        return response.data

    def create(self, data: dict) -> dict:
        response = supabase.table("category").insert(data).execute()
        return response.data[0]

    def remove(self, id: int) -> None:
        supabase.table("category").delete().eq("id", id).execute()
