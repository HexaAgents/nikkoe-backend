from app.dependencies import supabase
from app.repositories.base import batch_load


class ItemRepository:
    def find_all(self, limit: int = 50, offset: int = 0) -> dict:
        response = (
            supabase.table("item")
            .select("*", count="exact")
            .order("item_id")
            .range(offset, offset + limit - 1)
            .execute()
        )
        items = response.data or []
        total = response.count or 0

        item_ids = [i["id"] for i in items]
        if not item_ids:
            return {"data": [], "total": total}

        categories_map = batch_load("category", "id", list({i["category_id"] for i in items if i.get("category_id")}))

        stock_resp = supabase.table("stock").select("*").in_("item_id", item_ids).execute()
        stocks = stock_resp.data or []

        receipt_stock_resp = supabase.table("receipt_stock").select("*").execute()
        receipt_stocks = receipt_stock_resp.data or []

        stock_by_item: dict[int, list] = {}
        for s in stocks:
            loc_resp = (
                supabase.table("location").select("id, code").eq("id", s.get("location_id")).maybe_single().execute()
            )
            stock_by_item.setdefault(s["item_id"], []).append(
                {
                    "quantity": s.get("quantity"),
                    "locations": loc_resp.data,
                }
            )

        stock_id_to_item: dict[int, int] = {s["id"]: s["item_id"] for s in stocks}
        rs_by_item: dict[int, list] = {}
        for rs in receipt_stocks:
            iid = stock_id_to_item.get(rs.get("stock_id"))
            if iid:
                rs_by_item.setdefault(iid, []).append(
                    {
                        "unit_price": rs.get("unit_price"),
                    }
                )

        for item in items:
            iid = item["id"]
            item["categories"] = categories_map.get(item.get("category_id"))
            item["inventory_balances"] = stock_by_item.get(iid, [])
            item["receipt_lines"] = rs_by_item.get(iid, [])

        return {"data": items, "total": total}

    def find_by_id(self, id: int) -> dict | None:
        response = supabase.table("item").select("*, category(name)").eq("id", id).maybe_single().execute()
        return response.data

    def create(self, data: dict) -> dict:
        response = supabase.table("item").insert(data).execute()
        return response.data[0]

    def update(self, id: int, data: dict) -> dict:
        response = supabase.table("item").update(data).eq("id", id).execute()
        return response.data[0]

    def remove(self, id: int) -> None:
        supabase.table("item").delete().eq("id", id).execute()
