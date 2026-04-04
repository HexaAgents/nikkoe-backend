from postgrest.exceptions import APIError

from app.dependencies import supabase
from app.repositories.base import batch_load


class InventoryRepository:
    def find_movements(self, limit: int = 50, offset: int = 0) -> dict:
        response = (
            supabase.table("inventory_movements")
            .select("*", count="exact")
            .order("moved_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        movements = response.data or []
        total = response.count or 0

        item_ids = list({m["item_id"] for m in movements if m.get("item_id")})
        user_ids = list({m["user_id"] for m in movements if m.get("user_id")})

        items_map = batch_load("items", "item_id", item_ids, "item_id, part_number")
        users_map = batch_load("users", "user_id", user_ids, "user_id, name")

        for m in movements:
            m["items"] = items_map.get(m.get("item_id"))
            m["users"] = users_map.get(m.get("user_id"))

        return {"data": movements, "total": total}

    def find_by_item_id(self, item_id: str) -> list:
        try:
            response = (
                supabase.table("inventory_balances")
                .select("*, locations(location_code)")
                .eq("item_id", item_id)
                .execute()
            )
            return response.data or []
        except APIError as e:
            if e.code == "PGRST205":
                return []
            raise

    def find_on_hand(self) -> list:
        try:
            response = (
                supabase.table("inventory_balances")
                .select("*")
                .gt("quantity_on_hand", 0)
                .execute()
            )
            return response.data or []
        except APIError as e:
            if e.code == "PGRST205":
                return []
            raise
