from postgrest.exceptions import APIError

from app.dependencies import supabase
from app.repositories.base import batch_load


def _safe_query_view(query):
    try:
        return query.execute().data or []
    except APIError as e:
        if e.code == "PGRST205":
            return []
        raise


class ItemRepository:
    def find_all(self, limit: int = 50, offset: int = 0) -> dict:
        response = (
            supabase.table("items")
            .select("*", count="exact")
            .order("part_number")
            .range(offset, offset + limit - 1)
            .execute()
        )
        items = response.data or []
        total = response.count or 0

        item_ids = [i["item_id"] for i in items]
        if not item_ids:
            return {"data": [], "total": total}

        categories_map = batch_load("categories", "category_id", 
            list({i["category_id"] for i in items if i.get("category_id")}))

        balances = _safe_query_view(
            supabase.table("inventory_balances")
            .select("*")
            .in_("item_id", item_ids)
        )

        rl_resp = (
            supabase.table("receipt_lines")
            .select("*")
            .in_("item_id", item_ids)
            .execute()
        )
        receipt_lines = rl_resp.data or []

        location_ids = list({b["location_id"] for b in balances if b.get("location_id")})
        locations_map = batch_load("locations", "location_id", location_ids)

        receipt_ids = list({rl["receipt_id"] for rl in receipt_lines if rl.get("receipt_id")})
        receipts_map = batch_load("receipts", "receipt_id", receipt_ids)

        bal_by_item: dict[str, list] = {}
        for b in balances:
            bal_by_item.setdefault(b["item_id"], []).append({
                "quantity_on_hand": b.get("quantity_on_hand"),
                "locations": locations_map.get(b.get("location_id")),
            })

        rl_by_item: dict[str, list] = {}
        for rl in receipt_lines:
            rl_by_item.setdefault(rl["item_id"], []).append({
                "unit_cost": rl.get("unit_cost"),
                "receipts": receipts_map.get(rl.get("receipt_id")),
            })

        for item in items:
            iid = item["item_id"]
            item["categories"] = categories_map.get(item.get("category_id"))
            item["inventory_balances"] = bal_by_item.get(iid, [])
            item["receipt_lines"] = rl_by_item.get(iid, [])

        return {"data": items, "total": total}

    def find_by_id(self, id: str) -> dict | None:
        response = (
            supabase.table("items")
            .select("*, categories(name)")
            .eq("item_id", id)
            .maybe_single()
            .execute()
        )
        return response.data

    def create(self, data: dict) -> dict:
        response = (
            supabase.table("items").insert(data).select().single().execute()
        )
        return response.data

    def update(self, id: str, data: dict) -> dict:
        response = (
            supabase.table("items")
            .update(data)
            .eq("item_id", id)
            .select()
            .single()
            .execute()
        )
        return response.data

    def remove(self, id: str) -> None:
        supabase.table("items").delete().eq("item_id", id).execute()
