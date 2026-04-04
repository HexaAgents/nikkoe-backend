from app.dependencies import supabase
from app.repositories.base import batch_load


class SaleRepository:
    def find_all(self, limit: int = 50, offset: int = 0) -> dict:
        response = (
            supabase.table("sales")
            .select("*", count="exact")
            .order("sold_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        sales = response.data or []
        total = response.count or 0

        channel_ids = list({s["channel_id"] for s in sales if s.get("channel_id")})
        user_ids = list({s["user_id"] for s in sales if s.get("user_id")})

        channels_map = batch_load("channels", "channel_id", channel_ids)
        users_map = batch_load("users", "user_id", user_ids)

        for s in sales:
            s["channels"] = channels_map.get(s.get("channel_id"))
            s["users"] = users_map.get(s.get("user_id"))

        return {"data": sales, "total": total}

    def find_by_id(self, id: str) -> dict | None:
        response = (
            supabase.table("sales")
            .select("*, channels(channel_name), users(name)")
            .eq("sale_id", id)
            .maybe_single()
            .execute()
        )
        return response.data

    def find_lines(self, sale_id: str) -> list:
        response = (
            supabase.table("sale_lines")
            .select("*, items(part_number), locations(location_code)")
            .eq("sale_id", sale_id)
            .order("created_at")
            .execute()
        )
        return response.data or []

    def find_by_item_id(self, item_id: str) -> list:
        response = (
            supabase.table("sale_lines")
            .select("*, sales(sale_id, sold_at, channels(channel_name)), locations(location_code)")
            .eq("item_id", item_id)
            .order("created_at", desc=True)
            .execute()
        )
        return response.data or []

    def create(self, sale: dict, lines: list[dict]) -> dict:
        response = supabase.rpc("create_sale", {"p_sale": sale, "p_lines": lines}).execute()
        return response.data

    def void_sale(self, sale_id: str, user_id: str, reason: str) -> None:
        supabase.rpc(
            "void_sale",
            {"p_sale_id": sale_id, "p_user_id": user_id, "p_reason": reason},
        ).execute()
