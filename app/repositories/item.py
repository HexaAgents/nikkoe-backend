from app.dependencies import supabase
from app.repositories.base import dash_insensitive_pattern as _dash_insensitive_pattern, paginated_fetch


def _enrich_items(rows: list) -> list:
    for item in rows:
        item["categories"] = item.pop("category", None)
        stock_rows = item.pop("stock", [])
        item["total_quantity"] = sum(s.get("quantity", 0) for s in stock_rows)
        item["locations"] = sorted(
            {
                s["location"]["code"]
                for s in stock_rows
                if s.get("quantity", 0) > 0 and s.get("location") and s["location"].get("code")
            }
        )
    return rows


class ItemRepository:
    def find_all(self, limit: int = 20, offset: int = 0) -> dict:
        query = (
            supabase.table("item")
            .select("*, category(name), stock(quantity, location(code))", count="exact")
            .order("item_id")
        )
        rows, total = paginated_fetch(query, offset=offset, limit=limit)
        return {"data": _enrich_items(rows), "total": total}

    def search(self, query: str, limit: int = 20, offset: int = 0, *, in_stock: bool = False) -> dict:
        q = (
            supabase.table("item")
            .select("*, category(name), stock(quantity, location(code))", count="exact")
            .filter("item_id", "imatch", _dash_insensitive_pattern(query))
            .order("item_id")
        )
        rows, total = paginated_fetch(q, offset=offset, limit=limit)
        items = _enrich_items(rows)

        if in_stock:
            items.sort(key=lambda x: (x["total_quantity"] <= 0, x.get("item_id", "")))

        return {"data": items, "total": total}

    def find_by_category(self, category_id: int, limit: int = 5000, offset: int = 0) -> dict:
        query = (
            supabase.table("item")
            .select("*, category(name), stock(quantity, location(code))", count="exact")
            .eq("category_id", category_id)
            .order("item_id")
        )
        rows, total = paginated_fetch(query, offset=offset, limit=limit)
        return {"data": _enrich_items(rows), "total": total}

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
