from app.dependencies import supabase
from app.repositories.base import batch_load


class SaleRepository:
    def find_all(self, limit: int = 50, offset: int = 0) -> dict:
        response = (
            supabase.table("Sale")
            .select("*", count="exact")
            .order("date", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        sales = response.data or []
        total = response.count or 0

        channel_ids = list({s["channel_id_id"] for s in sales if s.get("channel_id_id")})
        user_ids = list({s["user_id"] for s in sales if s.get("user_id")})
        customer_ids = list({s["customer_id_id"] for s in sales if s.get("customer_id_id")})

        channels_map = batch_load("Channel", "id", channel_ids)
        users_map = batch_load("User", "id", user_ids, "id, first_name, last_name")
        customers_map = batch_load("Customer", "id", customer_ids, "id, name")

        for s in sales:
            s["channels"] = channels_map.get(s.get("channel_id_id"))
            s["users"] = users_map.get(s.get("user_id"))
            s["customers"] = customers_map.get(s.get("customer_id_id"))

        return {"data": sales, "total": total}

    def find_by_id(self, id: int) -> dict | None:
        response = (
            supabase.table("Sale")
            .select("*")
            .eq("id", id)
            .maybe_single()
            .execute()
        )
        sale = response.data
        if not sale:
            return None

        if sale.get("channel_id_id"):
            ch = supabase.table("Channel").select("*").eq("id", sale["channel_id_id"]).maybe_single().execute()
            sale["channels"] = ch.data
        if sale.get("user_id"):
            u = supabase.table("User").select("id, first_name, last_name").eq("id", sale["user_id"]).maybe_single().execute()
            sale["users"] = u.data
        if sale.get("customer_id_id"):
            c = supabase.table("Customer").select("id, name").eq("id", sale["customer_id_id"]).maybe_single().execute()
            sale["customers"] = c.data

        return sale

    def find_lines(self, sale_id: int) -> list:
        response = (
            supabase.table("Sale_Stock")
            .select("*")
            .eq("sale_id", sale_id)
            .execute()
        )
        lines = response.data or []

        stock_ids = list({ln["stock_id"] for ln in lines if ln.get("stock_id")})
        currency_ids = list({ln["currency_id"] for ln in lines if ln.get("currency_id")})
        stocks_map = batch_load("Stock", "id", stock_ids)
        currencies_map = batch_load("Currency", "id", currency_ids)

        for ln in lines:
            stock = stocks_map.get(ln.get("stock_id"))
            ln["stock"] = stock
            ln["currencies"] = currencies_map.get(ln.get("currency_id"))
            if stock:
                item_resp = supabase.table("Item").select("id, item_id").eq("id", stock.get("item_id")).maybe_single().execute()
                loc_resp = supabase.table("Location").select("id, code").eq("id", stock.get("location_id")).maybe_single().execute()
                ln["items"] = item_resp.data
                ln["locations"] = loc_resp.data

        return lines

    def find_by_item_id(self, item_id: int) -> list:
        stock_resp = supabase.table("Stock").select("id").eq("item_id", item_id).execute()
        stock_ids = [s["id"] for s in (stock_resp.data or [])]
        if not stock_ids:
            return []

        response = (
            supabase.table("Sale_Stock")
            .select("*")
            .in_("stock_id", stock_ids)
            .execute()
        )
        return response.data or []

    def create(self, sale: dict, lines: list[dict]) -> dict:
        sale_resp = supabase.table("Sale").insert(sale).execute()
        sale_row = sale_resp.data[0]
        sale_id = sale_row["id"]

        for line in lines:
            stock_id = line.pop("stock_id", None)
            item_id = line.pop("item_id", None)
            location_id = line.pop("location_id", None)

            if not stock_id and item_id and location_id:
                try:
                    existing = (
                        supabase.table("Stock")
                        .select("id")
                        .eq("item_id", item_id)
                        .eq("location_id", location_id)
                        .maybe_single()
                        .execute()
                    )
                    if existing and existing.data:
                        stock_id = existing.data["id"]
                except Exception:
                    existing = None

                if not stock_id:
                    new_stock = supabase.table("Stock").insert({"item_id": item_id, "location_id": location_id, "quantity": 0}).execute()
                    stock_id = new_stock.data[0]["id"]

            line["sale_id"] = sale_id
            if stock_id:
                line["stock_id"] = stock_id
            supabase.table("Sale_Stock").insert(line).execute()

            if stock_id:
                stock_row = supabase.table("Stock").select("quantity").eq("id", stock_id).single().execute()
                new_qty = (stock_row.data.get("quantity") or 0) - line.get("quantity", 0)
                supabase.table("Stock").update({"quantity": new_qty}).eq("id", stock_id).execute()

        return sale_row

    def void_sale(self, sale_id: int, user_id: int, reason: str) -> None:
        from datetime import datetime, timezone

        supabase.table("Sale").update({
            "status": "VOIDED",
            "void_reason": reason,
            "voided_at": datetime.now(timezone.utc).isoformat(),
            "voided_by": user_id,
        }).eq("id", sale_id).execute()
