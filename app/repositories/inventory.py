from app.dependencies import supabase
from app.repositories.base import batch_load


class InventoryRepository:
    def find_movements(self, limit: int = 50, offset: int = 0) -> dict:
        response = (
            supabase.table("transfer")
            .select("*", count="exact")
            .order("date", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        movements = response.data or []
        total = response.count or 0

        stock_from_ids = list({m["stock_id_from_id"] for m in movements if m.get("stock_id_from_id")})
        stock_to_ids = list({m["stock_id_to_id"] for m in movements if m.get("stock_id_to_id")})
        user_ids = list({m["user_id"] for m in movements if m.get("user_id")})

        all_stock_ids = list(set(stock_from_ids + stock_to_ids))
        stocks_map = batch_load("stock", "id", all_stock_ids)
        users_map = batch_load("user", "id", user_ids, "id, first_name, last_name")

        item_ids = list({s.get("item_id") for s in stocks_map.values() if s.get("item_id")})
        items_map = batch_load("item", "id", item_ids, "id, item_id")

        for m in movements:
            m["users"] = users_map.get(m.get("user_id"))
            from_stock = stocks_map.get(m.get("stock_id_from_id"))
            to_stock = stocks_map.get(m.get("stock_id_to_id"))
            m["from_stock"] = from_stock
            m["to_stock"] = to_stock
            if from_stock:
                m["items"] = items_map.get(from_stock.get("item_id"))
            elif to_stock:
                m["items"] = items_map.get(to_stock.get("item_id"))

        return {"data": movements, "total": total}

    def find_by_item_id(self, item_id: int) -> list:
        response = supabase.table("stock").select("*, location(code)").eq("item_id", item_id).execute()
        return response.data or []

    def find_on_hand(self) -> list:
        response = supabase.table("stock").select("*").gt("quantity", 0).execute()
        return response.data or []

    def create_transfer(self, from_stock_id: int, to_location_id: int, quantity: int, user_id: int | None = None, notes: str | None = None) -> dict:
        response = supabase.rpc("transfer_stock", {
            "p_from_stock_id": from_stock_id,
            "p_to_location_id": to_location_id,
            "p_quantity": quantity,
            "p_user_id": user_id,
            "p_notes": notes,
        }).execute()
        return response.data
