from app.dependencies import supabase
from app.repositories.base import batch_in_load, batch_load, paginated_fetch


class ReceiptRepository:
    def _enrich(self, receipts: list[dict]) -> list[dict]:
        user_ids = list({r["user_id"] for r in receipts if r.get("user_id")})
        users_map = batch_load("user", "id", user_ids, "id, first_name, last_name")

        receipt_ids = [r["id"] for r in receipts]
        line_supplier_map: dict[int, int] = {}
        if receipt_ids:
            lines_data = batch_in_load("receipt_stock", "receipt_id, supplier_id", "receipt_id", receipt_ids)
            for ln in lines_data:
                if ln.get("supplier_id") and ln["receipt_id"] not in line_supplier_map:
                    line_supplier_map[ln["receipt_id"]] = ln["supplier_id"]

        header_supplier_ids = list({r["supplier_id"] for r in receipts if r.get("supplier_id")})
        line_supplier_ids = list(set(line_supplier_map.values()))
        all_supplier_ids = list(set(header_supplier_ids + line_supplier_ids))
        suppliers_map = batch_load("supplier", "id", all_supplier_ids)

        for r in receipts:
            sup_id = r.get("supplier_id") or line_supplier_map.get(r["id"])
            r["suppliers"] = suppliers_map.get(sup_id) if sup_id else None
            r["users"] = users_map.get(r.get("user_id"))

        return receipts

    def find_all(self, limit: int = 50, offset: int = 0) -> dict:
        query = supabase.table("receipt").select("*", count="exact").order("dateTime", desc=True)
        receipts, total = paginated_fetch(query, offset=offset, limit=limit)
        return {"data": self._enrich(receipts), "total": total}

    def search_by_part_number(self, search_term: str, limit: int = 500) -> dict:
        rpc_resp = supabase.rpc(
            "search_receipts_by_part_number",
            {"search_term": search_term, "lim": limit},
        ).execute()
        receipt_ids = rpc_resp.data or []
        if not receipt_ids:
            return {"data": [], "total": 0}

        response = (
            supabase.table("receipt")
            .select("*", count="exact")
            .in_("id", receipt_ids)
            .order("dateTime", desc=True)
            .execute()
        )
        receipts = response.data or []
        total = response.count or 0

        return {"data": self._enrich(receipts), "total": total}

    def find_by_id(self, id: int) -> dict | None:
        response = supabase.table("receipt").select("*").eq("id", id).maybe_single().execute()
        receipt = response.data
        if not receipt:
            return None

        if receipt.get("supplier_id"):
            sup_resp = supabase.table("supplier").select("*").eq("id", receipt["supplier_id"]).maybe_single().execute()
            receipt["suppliers"] = sup_resp.data

        if receipt.get("user_id"):
            usr_resp = (
                supabase.table("user")
                .select("id, first_name, last_name")
                .eq("id", receipt["user_id"])
                .maybe_single()
                .execute()
            )
            receipt["users"] = usr_resp.data

        return receipt

    def find_lines(self, receipt_id: int) -> list:
        response = supabase.table("receipt_stock").select("*").eq("receipt_id", receipt_id).execute()
        lines = response.data or []

        stock_ids = list({ln["stock_id"] for ln in lines if ln.get("stock_id")})
        currency_ids = list({ln["currency_id"] for ln in lines if ln.get("currency_id")})
        supplier_ids = list({ln["supplier_id"] for ln in lines if ln.get("supplier_id")})
        stocks_map = batch_load("stock", "id", stock_ids)
        currencies_map = batch_load("currency", "id", currency_ids)
        suppliers_map = batch_load("supplier", "id", supplier_ids)

        for ln in lines:
            stock = stocks_map.get(ln.get("stock_id"))
            ln["stock"] = stock
            ln["currencies"] = currencies_map.get(ln.get("currency_id"))
            ln["suppliers"] = suppliers_map.get(ln.get("supplier_id"))
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

        response = supabase.table("receipt_stock").select("*").in_("stock_id", stock_ids).execute()
        lines = response.data or []
        if not lines:
            return []

        receipt_ids = list({ln["receipt_id"] for ln in lines if ln.get("receipt_id")})
        currency_ids = list({ln["currency_id"] for ln in lines if ln.get("currency_id")})
        supplier_ids = list({ln["supplier_id"] for ln in lines if ln.get("supplier_id")})
        location_ids = list(
            {
                stocks_map[ln["stock_id"]]["location_id"]
                for ln in lines
                if ln.get("stock_id") and stocks_map.get(ln["stock_id"], {}).get("location_id")
            }
        )

        receipts_map = batch_load("receipt", "id", receipt_ids)
        currencies_map = batch_load("currency", "id", currency_ids)
        suppliers_map = batch_load("supplier", "id", supplier_ids, "id, name")
        locations_map = batch_load("location", "id", location_ids)

        receipt_supplier_ids = list({r.get("supplier_id") for r in receipts_map.values() if r.get("supplier_id")})
        receipt_user_ids = list({r.get("user_id") for r in receipts_map.values() if r.get("user_id")})
        receipt_suppliers_map = batch_load("supplier", "id", receipt_supplier_ids, "id, name")
        users_map = batch_load("user", "id", receipt_user_ids, "id, first_name, last_name")

        result = []
        for ln in lines:
            receipt = receipts_map.get(ln.get("receipt_id"), {})
            stock = stocks_map.get(ln.get("stock_id"), {})
            line_supplier = suppliers_map.get(ln.get("supplier_id"))
            receipt_supplier = receipt_suppliers_map.get(receipt.get("supplier_id"))

            result.append(
                {
                    "id": ln["id"],
                    "receipt_id": ln.get("receipt_id"),
                    "quantity": ln.get("quantity"),
                    "unit_price": ln.get("unit_price"),
                    "date": receipt.get("dateTime"),
                    "status": receipt.get("status"),
                    "reference": receipt.get("reference"),
                    "note": receipt.get("note"),
                    "suppliers": line_supplier or receipt_supplier,
                    "users": users_map.get(receipt.get("user_id")),
                    "currencies": currencies_map.get(ln.get("currency_id")),
                    "locations": locations_map.get(stock.get("location_id")),
                }
            )

        result.sort(key=lambda r: r.get("date") or "", reverse=True)
        return result

    def find_by_supplier_id(self, supplier_id: int) -> list:
        line_resp = supabase.table("receipt_stock").select("*").eq("supplier_id", supplier_id).execute()
        line_lines = line_resp.data or []

        header_resp = supabase.table("receipt").select("id").eq("supplier_id", supplier_id).execute()
        header_receipt_ids = [r["id"] for r in (header_resp.data or [])]

        extra_lines: list[dict] = batch_in_load("receipt_stock", "*", "receipt_id", header_receipt_ids)

        seen_ids: set[int] = set()
        lines: list[dict] = []
        for ln in line_lines + extra_lines:
            if ln["id"] not in seen_ids:
                seen_ids.add(ln["id"])
                lines.append(ln)

        if not lines:
            return []

        stock_ids = list({ln["stock_id"] for ln in lines if ln.get("stock_id")})
        receipt_ids = list({ln["receipt_id"] for ln in lines if ln.get("receipt_id")})
        currency_ids = list({ln["currency_id"] for ln in lines if ln.get("currency_id")})

        stocks_map = batch_load("stock", "id", stock_ids)
        receipts_map = batch_load("receipt", "id", receipt_ids)
        currencies_map = batch_load("currency", "id", currency_ids)

        item_ids = list({s.get("item_id") for s in stocks_map.values() if s.get("item_id")})
        location_ids = list({s.get("location_id") for s in stocks_map.values() if s.get("location_id")})
        items_map = batch_load("item", "id", item_ids, "id, item_id")
        locations_map = batch_load("location", "id", location_ids)

        receipt_user_ids = list({r.get("user_id") for r in receipts_map.values() if r.get("user_id")})
        users_map = batch_load("user", "id", receipt_user_ids, "id, first_name, last_name")

        result = []
        for ln in lines:
            receipt = receipts_map.get(ln.get("receipt_id"), {})
            stock = stocks_map.get(ln.get("stock_id"), {})

            result.append(
                {
                    "id": ln["id"],
                    "receipt_id": ln.get("receipt_id"),
                    "quantity": ln.get("quantity"),
                    "unit_price": ln.get("unit_price"),
                    "date": receipt.get("dateTime"),
                    "status": receipt.get("status"),
                    "reference": receipt.get("reference"),
                    "note": receipt.get("note"),
                    "items": items_map.get(stock.get("item_id")),
                    "users": users_map.get(receipt.get("user_id")),
                    "currencies": currencies_map.get(ln.get("currency_id")),
                    "locations": locations_map.get(stock.get("location_id")),
                }
            )

        result.sort(key=lambda r: r.get("date") or "", reverse=True)
        return result

    def create(self, receipt: dict, lines: list[dict]) -> dict:
        from datetime import datetime, timezone

        if not receipt.get("dateTime"):
            receipt["dateTime"] = datetime.now(timezone.utc).isoformat()

        receipt = {k: v for k, v in receipt.items() if v is not None}
        receipt_resp = supabase.table("receipt").insert(receipt).execute()
        receipt_row = receipt_resp.data[0]
        receipt_id = receipt_row["id"]

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

            line["receipt_id"] = receipt_id
            if stock_id:
                line["stock_id"] = stock_id
            supabase.table("receipt_stock").insert(line).execute()

            if stock_id:
                stock_row = supabase.table("stock").select("quantity").eq("id", stock_id).single().execute()
                new_qty = (stock_row.data.get("quantity") or 0) + line.get("quantity", 0)
                supabase.table("stock").update({"quantity": new_qty}).eq("id", stock_id).execute()

        return receipt_row

    def void_receipt(self, receipt_id: int, user_id: int, reason: str) -> None:
        from datetime import datetime, timezone

        lines_resp = supabase.table("receipt_stock").select("stock_id, quantity").eq("receipt_id", receipt_id).execute()
        for line in lines_resp.data or []:
            stock_id = line.get("stock_id")
            qty = line.get("quantity", 0)
            if stock_id and qty:
                stock_row = supabase.table("stock").select("quantity").eq("id", stock_id).single().execute()
                restored_qty = (stock_row.data.get("quantity") or 0) - qty
                supabase.table("stock").update({"quantity": restored_qty}).eq("id", stock_id).execute()

        supabase.table("receipt").update(
            {
                "status": "VOIDED",
                "void_reason": reason,
                "voided_at": datetime.now(timezone.utc).isoformat(),
                "voided_by": user_id,
            }
        ).eq("id", receipt_id).execute()
