from app.dependencies import supabase
from app.repositories.base import batch_load


class ReceiptRepository:
    def find_all(self, limit: int = 50, offset: int = 0) -> dict:
        response = (
            supabase.table("Receipt")
            .select("*", count="exact")
            .order("dateTime", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        receipts = response.data or []
        total = response.count or 0

        supplier_ids = list({r["supplier_id"] for r in receipts if r.get("supplier_id")})
        user_ids = list({r["user_id"] for r in receipts if r.get("user_id")})

        suppliers_map = batch_load("Supplier", "id", supplier_ids)
        users_map = batch_load("User", "id", user_ids, "id, first_name, last_name")

        for r in receipts:
            r["suppliers"] = suppliers_map.get(r.get("supplier_id"))
            r["users"] = users_map.get(r.get("user_id"))

        return {"data": receipts, "total": total}

    def find_by_id(self, id: int) -> dict | None:
        response = supabase.table("Receipt").select("*").eq("id", id).maybe_single().execute()
        receipt = response.data
        if not receipt:
            return None

        if receipt.get("supplier_id"):
            sup_resp = supabase.table("Supplier").select("*").eq("id", receipt["supplier_id"]).maybe_single().execute()
            receipt["suppliers"] = sup_resp.data

        if receipt.get("user_id"):
            usr_resp = supabase.table("User").select("id, first_name, last_name").eq("id", receipt["user_id"]).maybe_single().execute()
            receipt["users"] = usr_resp.data

        return receipt

    def find_lines(self, receipt_id: int) -> list:
        response = (
            supabase.table("Receipt_Stock")
            .select("*")
            .eq("receipt_id", receipt_id)
            .execute()
        )
        lines = response.data or []

        stock_ids = list({ln["stock_id"] for ln in lines if ln.get("stock_id")})
        currency_ids = list({ln["currency_id"] for ln in lines if ln.get("currency_id")})
        supplier_ids = list({ln["supplier_id"] for ln in lines if ln.get("supplier_id")})
        stocks_map = batch_load("Stock", "id", stock_ids)
        currencies_map = batch_load("Currency", "id", currency_ids)
        suppliers_map = batch_load("Supplier", "id", supplier_ids)

        for ln in lines:
            stock = stocks_map.get(ln.get("stock_id"))
            ln["stock"] = stock
            ln["currencies"] = currencies_map.get(ln.get("currency_id"))
            ln["suppliers"] = suppliers_map.get(ln.get("supplier_id"))
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
            supabase.table("Receipt_Stock")
            .select("*")
            .in_("stock_id", stock_ids)
            .execute()
        )
        return response.data or []

    def create(self, receipt: dict, lines: list[dict]) -> dict:
        receipt_resp = supabase.table("Receipt").insert(receipt).select().single().execute()
        receipt_row = receipt_resp.data
        receipt_id = receipt_row["id"]

        for line in lines:
            stock_id = line.pop("stock_id", None)
            item_id = line.pop("item_id", None)
            location_id = line.pop("location_id", None)

            if not stock_id and item_id and location_id:
                existing = (
                    supabase.table("Stock")
                    .select("id")
                    .eq("item_id", item_id)
                    .eq("location_id", location_id)
                    .maybe_single()
                    .execute()
                )
                if existing.data:
                    stock_id = existing.data["id"]
                else:
                    new_stock = supabase.table("Stock").insert({"item_id": item_id, "location_id": location_id, "quantity": 0}).select().single().execute()
                    stock_id = new_stock.data["id"]

            line["receipt_id"] = receipt_id
            line["stock_id"] = stock_id
            supabase.table("Receipt_Stock").insert(line).execute()

            if stock_id:
                stock_row = supabase.table("Stock").select("quantity").eq("id", stock_id).single().execute()
                new_qty = (stock_row.data.get("quantity") or 0) + line.get("quantity", 0)
                supabase.table("Stock").update({"quantity": new_qty}).eq("id", stock_id).execute()

        return receipt_row

    def void_receipt(self, receipt_id: int, user_id: int, reason: str) -> None:
        from datetime import datetime, timezone

        supabase.table("Receipt").update({
            "status": "VOIDED",
            "void_reason": reason,
            "voided_at": datetime.now(timezone.utc).isoformat(),
            "voided_by": user_id,
        }).eq("id", receipt_id).execute()
