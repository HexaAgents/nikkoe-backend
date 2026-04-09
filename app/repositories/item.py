from app.dependencies import supabase
from app.repositories.base import (
    batch_in_load,
    dash_insensitive_pattern as _dash_insensitive_pattern,
    paginated_fetch,
)

_SORTED_SORT_OPTIONS = {"latest_receipt", "latest_sale", "total_quantity"}
_ITEM_SELECT = "*, category(name), stock(quantity, location(code))"


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


def _load_and_enrich_by_ids(ids: list[int]) -> list[dict]:
    """Load full item rows (with category + stock) for the given IDs,
    returning them in the same order as *ids*."""
    if not ids:
        return []
    rows = batch_in_load("item", _ITEM_SELECT, "id", ids)
    enriched = _enrich_items(rows)
    by_id = {r["id"]: r for r in enriched}
    return [by_id[i] for i in ids if i in by_id]


class ItemRepository:
    def find_all(self, limit: int = 20, offset: int = 0, sort_by: str = "item_id") -> dict:
        if sort_by in _SORTED_SORT_OPTIONS:
            return self._find_sorted(sort_by, limit, offset)
        query = (
            supabase.table("item")
            .select(_ITEM_SELECT, count="exact")
            .order("item_id")
        )
        rows, total = paginated_fetch(query, offset=offset, limit=limit)
        return {"data": _enrich_items(rows), "total": total}

    def search(self, query: str, limit: int = 20, offset: int = 0, *,
               in_stock: bool = False, sort_by: str = "item_id") -> dict:
        if sort_by in _SORTED_SORT_OPTIONS:
            return self._find_sorted(sort_by, limit, offset, search=query)
        q = (
            supabase.table("item")
            .select(_ITEM_SELECT, count="exact")
            .filter("item_id", "imatch", _dash_insensitive_pattern(query))
            .order("item_id")
        )
        rows, total = paginated_fetch(q, offset=offset, limit=limit)
        items = _enrich_items(rows)

        if in_stock:
            items.sort(key=lambda x: (x["total_quantity"] <= 0, x.get("item_id", "")))

        return {"data": items, "total": total}

    def _find_sorted(self, sort_by: str, limit: int, offset: int,
                     search: str | None = None) -> dict:
        params: dict = {
            "p_sort_by": sort_by,
            "p_limit": limit,
            "p_offset": offset,
        }
        if search:
            params["p_search"] = search
        resp = supabase.rpc("get_items_sorted", params).execute()
        rpc_rows = resp.data or []
        if not rpc_rows:
            return {"data": [], "total": 0}
        total = rpc_rows[0].get("total_count", len(rpc_rows))
        ids = [r["id"] for r in rpc_rows]
        return {"data": _load_and_enrich_by_ids(ids), "total": total}

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
