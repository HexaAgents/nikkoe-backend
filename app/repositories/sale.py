from app.dependencies import supabase
from app.repositories.base import batch_load


class SaleRepository:
    def _enrich(self, sales: list[dict]) -> list[dict]:
        channel_ids = list({s["channel_id_id"] for s in sales if s.get("channel_id_id")})
        user_ids = list({s["user_id"] for s in sales if s.get("user_id")})
        customer_ids = list({s["customer_id_id"] for s in sales if s.get("customer_id_id")})

        channels_map = batch_load("channel", "id", channel_ids)
        users_map = batch_load("user", "id", user_ids, "id, first_name, last_name")
        customers_map = batch_load("customer", "id", customer_ids, "id, name")

        for s in sales:
            s["channels"] = channels_map.get(s.get("channel_id_id"))
            s["users"] = users_map.get(s.get("user_id"))
            s["customers"] = customers_map.get(s.get("customer_id_id"))

        return sales

    def find_all(self, limit: int = 50, offset: int = 0) -> dict:
        response = (
            supabase.table("sale")
            .select("*", count="exact")
            .order("date", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        sales = response.data or []
        total = response.count or 0

        return {"data": self._enrich(sales), "total": total}

    def search_by_part_number(self, search_term: str, limit: int = 500) -> dict:
        rpc_resp = supabase.rpc(
            "search_sales_by_part_number",
            {"search_term": search_term, "lim": limit},
        ).execute()
        sale_ids = rpc_resp.data or []
        if not sale_ids:
            return {"data": [], "total": 0}

        response = (
            supabase.table("sale").select("*", count="exact").in_("id", sale_ids).order("date", desc=True).execute()
        )
        sales = response.data or []
        total = response.count or 0

        return {"data": self._enrich(sales), "total": total}

    def find_by_id(self, id: int) -> dict | None:
        response = supabase.table("sale").select("*").eq("id", id).maybe_single().execute()
        sale = response.data
        if not sale:
            return None

        if sale.get("channel_id_id"):
            ch = supabase.table("channel").select("*").eq("id", sale["channel_id_id"]).maybe_single().execute()
            sale["channels"] = ch.data
        if sale.get("user_id"):
            u = (
                supabase.table("user")
                .select("id, first_name, last_name")
                .eq("id", sale["user_id"])
                .maybe_single()
                .execute()
            )
            sale["users"] = u.data
        if sale.get("customer_id_id"):
            c = supabase.table("customer").select("id, name").eq("id", sale["customer_id_id"]).maybe_single().execute()
            sale["customers"] = c.data

        return sale

    def find_lines(self, sale_id: int) -> list:
        response = supabase.table("sale_stock").select("*").eq("sale_id", sale_id).execute()
        lines = response.data or []

        stock_ids = list({ln["stock_id"] for ln in lines if ln.get("stock_id")})
        currency_ids = list({ln["currency_id"] for ln in lines if ln.get("currency_id")})
        stocks_map = batch_load("stock", "id", stock_ids)
        currencies_map = batch_load("currency", "id", currency_ids)

        for ln in lines:
            stock = stocks_map.get(ln.get("stock_id"))
            ln["stock"] = stock
            ln["currencies"] = currencies_map.get(ln.get("currency_id"))
            if stock:
                item_resp = (
                    supabase.table("item").select("id, item_id").eq("id", stock.get("item_id")).maybe_single().execute()
                )
                loc_resp = (
                    supabase.table("location")
                    .select("id, code")
                    .eq("id", stock.get("location_id"))
                    .maybe_single()
                    .execute()
                )
                ln["items"] = item_resp.data
                ln["locations"] = loc_resp.data

        return lines

    def find_by_item_id(self, item_id: int) -> list:
        stock_resp = supabase.table("stock").select("id, location_id").eq("item_id", item_id).execute()
        stocks = stock_resp.data or []
        if not stocks:
            return []

        stock_ids = [s["id"] for s in stocks]
        stocks_map = {s["id"]: s for s in stocks}

        response = supabase.table("sale_stock").select("*").in_("stock_id", stock_ids).execute()
        lines = response.data or []
        if not lines:
            return []

        sale_ids = list({ln["sale_id"] for ln in lines if ln.get("sale_id")})
        currency_ids = list({ln["currency_id"] for ln in lines if ln.get("currency_id")})
        location_ids = list(
            {
                stocks_map[ln["stock_id"]]["location_id"]
                for ln in lines
                if ln.get("stock_id") and stocks_map.get(ln["stock_id"], {}).get("location_id")
            }
        )

        sales_map = batch_load("sale", "id", sale_ids)
        currencies_map = batch_load("currency", "id", currency_ids)
        locations_map = batch_load("location", "id", location_ids)

        customer_ids = list({s.get("customer_id_id") for s in sales_map.values() if s.get("customer_id_id")})
        channel_ids = list({s.get("channel_id_id") for s in sales_map.values() if s.get("channel_id_id")})
        user_ids = list({s.get("user_id") for s in sales_map.values() if s.get("user_id")})

        customers_map = batch_load("customer", "id", customer_ids, "id, name")
        channels_map = batch_load("channel", "id", channel_ids)
        users_map = batch_load("user", "id", user_ids, "id, first_name, last_name")

        result = []
        for ln in lines:
            sale = sales_map.get(ln.get("sale_id"), {})
            stock = stocks_map.get(ln.get("stock_id"), {})

            result.append(
                {
                    "id": ln["id"],
                    "sale_id": ln.get("sale_id"),
                    "quantity": ln.get("quantity"),
                    "unit_price": ln.get("unit_price"),
                    "date": sale.get("date"),
                    "status": sale.get("status"),
                    "note": sale.get("note"),
                    "channel_ref": sale.get("channel_ref"),
                    "customers": customers_map.get(sale.get("customer_id_id")),
                    "channels": channels_map.get(sale.get("channel_id_id")),
                    "users": users_map.get(sale.get("user_id")),
                    "currencies": currencies_map.get(ln.get("currency_id")),
                    "locations": locations_map.get(stock.get("location_id")),
                }
            )

        result.sort(key=lambda r: r.get("date") or "", reverse=True)
        return result

    def create(self, sale: dict, lines: list[dict]) -> dict:
        from datetime import datetime, timezone

        if not sale.get("date"):
            sale["date"] = datetime.now(timezone.utc).isoformat()

        sale = {k: v for k, v in sale.items() if v is not None}
        sale_resp = supabase.table("sale").insert(sale).execute()
        sale_row = sale_resp.data[0]
        sale_id = sale_row["id"]

        for line in lines:
            stock_id = line.pop("stock_id", None)
            item_id = line.pop("item_id", None)
            location_id = line.pop("location_id", None)

            if not stock_id and item_id and location_id:
                try:
                    existing = (
                        supabase.table("stock")
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
                    new_stock = (
                        supabase.table("stock")
                        .insert({"item_id": item_id, "location_id": location_id, "quantity": 0})
                        .execute()
                    )
                    stock_id = new_stock.data[0]["id"]

            line["sale_id"] = sale_id
            if stock_id:
                line["stock_id"] = stock_id
            supabase.table("sale_stock").insert(line).execute()

            if stock_id:
                stock_row = supabase.table("stock").select("quantity").eq("id", stock_id).single().execute()
                new_qty = (stock_row.data.get("quantity") or 0) - line.get("quantity", 0)
                supabase.table("stock").update({"quantity": new_qty}).eq("id", stock_id).execute()

        return sale_row

    def void_sale(self, sale_id: int, user_id: int, reason: str) -> None:
        from datetime import datetime, timezone

        lines_resp = supabase.table("sale_stock").select("stock_id, quantity").eq("sale_id", sale_id).execute()
        for line in lines_resp.data or []:
            stock_id = line.get("stock_id")
            qty = line.get("quantity", 0)
            if stock_id and qty:
                stock_row = supabase.table("stock").select("quantity").eq("id", stock_id).single().execute()
                restored_qty = (stock_row.data.get("quantity") or 0) + qty
                supabase.table("stock").update({"quantity": restored_qty}).eq("id", stock_id).execute()

        supabase.table("sale").update(
            {
                "status": "VOIDED",
                "void_reason": reason,
                "voided_at": datetime.now(timezone.utc).isoformat(),
                "voided_by": user_id,
            }
        ).eq("id", sale_id).execute()
