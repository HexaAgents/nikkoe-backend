from app.dependencies import supabase
from app.repositories.base import batch_in_load, batch_load, dash_insensitive_pattern, paginated_fetch, retry_transient

_LIST_SELECT = (
    "*, "
    "channels:channel!channel_id_id(id, name), "
    "users:user!user_id(id, first_name, last_name), "
    "customers:customer!customer_id_id(id, name)"
)


class SaleRepository:
    @retry_transient()
    def find_all(self, limit: int = 50, offset: int = 0, status: str | None = None) -> dict:
        query = supabase.table("sale").select(_LIST_SELECT, count="exact").order("date", desc=True)
        if status:
            query = query.eq("status", status)
        sales, total = paginated_fetch(query, offset=offset, limit=limit)
        return {"data": sales, "total": total}

    @retry_transient()
    def search_by_part_number(
        self,
        search_term: str,
        limit: int = 50,
        offset: int = 0,
        status: str | None = None,
    ) -> dict:
        matching_ids: set[int] = set()

        try:
            rpc_resp = supabase.rpc(
                "search_sales_by_part_number",
                {"search_term": search_term},
            ).execute()
            matching_ids.update(rpc_resp.data or [])
        except Exception:
            pass

        pattern = dash_insensitive_pattern(search_term)
        item_resp = supabase.table("item").select("id").filter("item_id", "imatch", pattern).execute()
        if item_resp.data:
            item_ids = [i["id"] for i in item_resp.data]
            stock_rows = batch_in_load("stock", "id", "item_id", item_ids)
            if stock_rows:
                stock_ids = [s["id"] for s in stock_rows]
                sale_stock_rows = batch_in_load("sale_stock", "sale_id", "stock_id", stock_ids)
                matching_ids.update(r["sale_id"] for r in sale_stock_rows if r.get("sale_id"))

        direct_resp = (
            supabase.table("sale")
            .select("id")
            .or_(f"note.ilike.%{search_term}%,channel_ref.ilike.%{search_term}%")
            .execute()
        )
        matching_ids.update(r["id"] for r in (direct_resp.data or []))

        cust_resp = supabase.table("customer").select("id").ilike("name", f"%{search_term}%").execute()
        if cust_resp.data:
            cust_ids = [c["id"] for c in cust_resp.data]
            sale_resp = supabase.table("sale").select("id").in_("customer_id_id", cust_ids).execute()
            matching_ids.update(r["id"] for r in (sale_resp.data or []))

        chan_resp = supabase.table("channel").select("id").ilike("name", f"%{search_term}%").execute()
        if chan_resp.data:
            chan_ids = [c["id"] for c in chan_resp.data]
            sale_resp = supabase.table("sale").select("id").in_("channel_id_id", chan_ids).execute()
            matching_ids.update(r["id"] for r in (sale_resp.data or []))

        if not matching_ids:
            return {"data": [], "total": 0}

        query = (
            supabase.table("sale")
            .select(_LIST_SELECT, count="exact")
            .in_("id", list(matching_ids))
            .order("date", desc=True)
        )
        if status:
            query = query.eq("status", status)
        sales, total = paginated_fetch(query, offset=offset, limit=limit)
        return {"data": sales, "total": total}

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
