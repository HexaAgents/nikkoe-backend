from app.dependencies import supabase

PAGE_SIZE = 1000


class ItemRepository:
    def find_all(self, limit: int = 100000, offset: int = 0) -> dict:
        all_items: list = []
        current_offset = offset
        remaining = limit

        while remaining > 0:
            batch = min(remaining, PAGE_SIZE)
            response = (
                supabase.table("item")
                .select("*, category(name), stock(quantity, location(code))", count="planned")
                .order("item_id")
                .range(current_offset, current_offset + batch - 1)
                .execute()
            )
            rows = response.data or []

            for item in rows:
                item["categories"] = item.pop("category", None)
                stock_rows = item.pop("stock", [])
                item["total_quantity"] = sum(s.get("quantity", 0) for s in stock_rows)
                item["locations"] = sorted(
                    {s["location"]["code"] for s in stock_rows if s.get("location") and s["location"].get("code")}
                )

            all_items.extend(rows)
            if len(rows) < batch:
                break
            current_offset += batch
            remaining -= batch

        return {"data": all_items, "total": len(all_items)}

    def search(self, query: str, limit: int = 1000, offset: int = 0) -> dict:
        response = (
            supabase.table("item")
            .select("*, category(name), stock(quantity, location(code))", count="planned")
            .ilike("item_id", f"*{query}*")
            .order("item_id")
            .range(offset, offset + min(limit, PAGE_SIZE) - 1)
            .execute()
        )
        items = response.data or []

        for item in items:
            item["categories"] = item.pop("category", None)
            stock_rows = item.pop("stock", [])
            item["total_quantity"] = sum(s.get("quantity", 0) for s in stock_rows)
            item["locations"] = sorted(
                {s["location"]["code"] for s in stock_rows if s.get("location") and s["location"].get("code")}
            )

        return {"data": items, "total": len(items)}

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
