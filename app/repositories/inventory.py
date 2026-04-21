from app.dependencies import supabase
from app.repositories.base import batch_load, dash_insensitive_pattern, paginated_fetch, retry_transient


class InventoryRepository:
    @retry_transient()
    def find_movements(self, limit: int = 50, offset: int = 0, search: str | None = None) -> dict:
        if search:
            return self._search_movements(search, limit, offset)
        query = supabase.table("transfer").select("*", count="exact").order("date", desc=True)
        movements, total = paginated_fetch(query, offset=offset, limit=limit)
        self._enrich_movements(movements)
        return {"data": movements, "total": total}

    def _search_movements(self, search_term: str, limit: int, offset: int) -> dict:
        from app.repositories.base import batch_in_load as _batch_in

        matching_ids: set[int] = set()

        notes_resp = supabase.table("transfer").select("id").ilike("notes", f"%{search_term}%").execute()
        matching_ids.update(r["id"] for r in (notes_resp.data or []))

        pattern = dash_insensitive_pattern(search_term)
        item_resp = supabase.table("item").select("id").filter("item_id", "imatch", pattern).execute()
        if item_resp.data:
            item_ids = [i["id"] for i in item_resp.data]
            stock_rows = _batch_in("stock", "id", "item_id", item_ids)
            if stock_rows:
                stock_ids = [s["id"] for s in stock_rows]
                from_rows = _batch_in("transfer", "id", "stock_id_from_id", stock_ids)
                to_rows = _batch_in("transfer", "id", "stock_id_to_id", stock_ids)
                matching_ids.update(r["id"] for r in from_rows)
                matching_ids.update(r["id"] for r in to_rows)

        if not matching_ids:
            return {"data": [], "total": 0}

        query = (
            supabase.table("transfer").select("*", count="exact").in_("id", list(matching_ids)).order("date", desc=True)
        )
        movements, total = paginated_fetch(query, offset=offset, limit=limit)
        self._enrich_movements(movements)
        return {"data": movements, "total": total}

    @staticmethod
    def _enrich_movements(movements: list) -> None:
        stock_from_ids = list({m["stock_id_from_id"] for m in movements if m.get("stock_id_from_id")})
        stock_to_ids = list({m["stock_id_to_id"] for m in movements if m.get("stock_id_to_id")})
        user_ids = list({m["user_id"] for m in movements if m.get("user_id")})

        all_stock_ids = list(set(stock_from_ids + stock_to_ids))
        stocks_map = batch_load("stock", "id", all_stock_ids)
        users_map = batch_load("user", "id", user_ids, "id, first_name, last_name")

        direct_item_ids = list(
            {m["from_item_id"] for m in movements if m.get("from_item_id")}
            | {m["to_item_id"] for m in movements if m.get("to_item_id")}
        )
        stock_item_ids = list({s.get("item_id") for s in stocks_map.values() if s.get("item_id")})
        all_item_ids = list(set(direct_item_ids + stock_item_ids))
        items_map = batch_load("item", "id", all_item_ids, "id, item_id, description")

        location_ids = list({s.get("location_id") for s in stocks_map.values() if s.get("location_id")})
        locations_map = batch_load("location", "id", location_ids, "id, code")

        for m in movements:
            m["users"] = users_map.get(m.get("user_id"))
            from_stock = stocks_map.get(m.get("stock_id_from_id"))
            to_stock = stocks_map.get(m.get("stock_id_to_id"))
            m["from_stock"] = from_stock
            m["to_stock"] = to_stock
            m["from_item"] = items_map.get(m.get("from_item_id")) or (
                items_map.get(from_stock.get("item_id")) if from_stock else None
            )
            m["to_item"] = items_map.get(m.get("to_item_id")) or (
                items_map.get(to_stock.get("item_id")) if to_stock else None
            )
            m["from_location"] = locations_map.get(from_stock.get("location_id")) if from_stock else None
            m["to_location"] = locations_map.get(to_stock.get("location_id")) if to_stock else None
            if from_stock:
                m["items"] = items_map.get(from_stock.get("item_id"))
            elif to_stock:
                m["items"] = items_map.get(to_stock.get("item_id"))

    @retry_transient()
    def find_by_item_id(self, item_id: int) -> list:
        response = supabase.table("stock").select("*, location(code)").eq("item_id", item_id).execute()
        return response.data or []

    @retry_transient()
    def find_transfers_by_item_id(self, item_id: int) -> list:
        stock_resp = supabase.table("stock").select("id, location_id, item_id").eq("item_id", item_id).execute()
        stocks = stock_resp.data or []
        if not stocks:
            return []

        stock_ids = [s["id"] for s in stocks]
        stocks_map = {s["id"]: s for s in stocks}

        from_resp = supabase.table("transfer").select("*").in_("stock_id_from_id", stock_ids).execute()
        to_resp = supabase.table("transfer").select("*").in_("stock_id_to_id", stock_ids).execute()

        seen = set()
        transfers = []
        for t in (from_resp.data or []) + (to_resp.data or []):
            if t["id"] not in seen:
                seen.add(t["id"])
                transfers.append(t)

        if not transfers:
            return []

        all_stock_ids = list(
            {t["stock_id_from_id"] for t in transfers if t.get("stock_id_from_id")}
            | {t["stock_id_to_id"] for t in transfers if t.get("stock_id_to_id")}
        )
        missing_ids = [sid for sid in all_stock_ids if sid not in stocks_map]
        if missing_ids:
            extra = batch_load("stock", "id", missing_ids, "id, location_id, item_id")
            stocks_map.update(extra)

        location_ids = list({s.get("location_id") for s in stocks_map.values() if s.get("location_id")})
        locations_map = batch_load("location", "id", location_ids, "id, code")

        all_item_ids = list(
            {t["from_item_id"] for t in transfers if t.get("from_item_id")}
            | {t["to_item_id"] for t in transfers if t.get("to_item_id")}
            | {s.get("item_id") for s in stocks_map.values() if s.get("item_id")}
        )
        items_map = batch_load("item", "id", all_item_ids, "id, item_id")

        user_ids = list({t["user_id"] for t in transfers if t.get("user_id")})
        users_map = batch_load("user", "id", user_ids, "id, first_name, last_name")

        result = []
        for t in transfers:
            from_stock = stocks_map.get(t.get("stock_id_from_id"), {})
            to_stock = stocks_map.get(t.get("stock_id_to_id"), {})
            from_item = items_map.get(t.get("from_item_id")) or items_map.get(from_stock.get("item_id"))
            to_item = items_map.get(t.get("to_item_id")) or items_map.get(to_stock.get("item_id"))
            result.append(
                {
                    "id": t["id"],
                    "quantity": t.get("quantity"),
                    "date": t.get("date"),
                    "notes": t.get("notes"),
                    "from_item": from_item,
                    "to_item": to_item,
                    "from_location": locations_map.get(from_stock.get("location_id")),
                    "to_location": locations_map.get(to_stock.get("location_id")),
                    "users": users_map.get(t.get("user_id")),
                }
            )

        result.sort(key=lambda r: r.get("date") or "", reverse=True)
        return result

    @retry_transient()
    def stock_valuation(self) -> list:
        try:
            return self._stock_valuation_view()
        except Exception:
            return self._stock_valuation_fallback()

    def _stock_valuation_view(self) -> list:
        all_rows: list = []
        page_size = 1000
        offset = 0
        while True:
            response = (
                supabase.table("v_stock_valuation")
                .select("*")
                .order("item_id")
                .range(offset, offset + page_size - 1)
                .execute()
            )
            batch = response.data or []
            all_rows.extend(batch)
            if len(batch) < page_size:
                break
            offset += page_size
        return all_rows

    def _stock_valuation_fallback(self) -> list:
        """Pre-migration fallback when v_stock_valuation view doesn't exist."""
        PAGE_SIZE = 1000

        all_items: list = []
        offset = 0
        while True:
            resp = (
                supabase.table("item")
                .select("id, item_id, description")
                .order("id")
                .range(offset, offset + PAGE_SIZE - 1)
                .execute()
            )
            batch = resp.data or []
            all_items.extend(batch)
            if len(batch) < PAGE_SIZE:
                break
            offset += PAGE_SIZE

        if not all_items:
            return []

        item_qty: dict[int, int] = {}
        stock_item_map: dict[int, int] = {}
        all_stock_ids: list[int] = []
        offset = 0
        while True:
            resp = (
                supabase.table("stock")
                .select("id, item_id, quantity")
                .order("id")
                .range(offset, offset + PAGE_SIZE - 1)
                .execute()
            )
            batch = resp.data or []
            for row in batch:
                stock_item_map[row["id"]] = row["item_id"]
                all_stock_ids.append(row["id"])
                item_qty[row["item_id"]] = item_qty.get(row["item_id"], 0) + row.get("quantity", 0)
            if len(batch) < PAGE_SIZE:
                break
            offset += PAGE_SIZE

        receipt_lines: list = []
        for i in range(0, len(all_stock_ids), PAGE_SIZE):
            batch_ids = all_stock_ids[i : i + PAGE_SIZE]
            resp = (
                supabase.table("receipt_stock")
                .select("stock_id, unit_price, receipt(dateTime, status)")
                .in_("stock_id", batch_ids)
                .execute()
            )
            receipt_lines.extend(resp.data or [])

        item_price_map: dict[int, dict] = {}
        for rl in receipt_lines:
            receipt = rl.get("receipt") or {}
            if receipt.get("status") == "VOIDED":
                continue
            iid = stock_item_map.get(rl.get("stock_id"))
            if iid is None:
                continue
            date = receipt.get("dateTime", "")
            existing = item_price_map.get(iid)
            if not existing or date > existing["date"]:
                item_price_map[iid] = {"date": date, "unit_price": rl.get("unit_price")}

        result = []
        for item in all_items:
            pk = item["id"]
            price_info = item_price_map.get(pk)
            unit_price = price_info["unit_price"] if price_info else None
            total_qty = item_qty.get(pk, 0)
            result.append(
                {
                    "item_id": item.get("item_id", ""),
                    "description": item.get("description"),
                    "total_quantity": total_qty,
                    "unit_price": unit_price,
                    "stock_valuation": round(unit_price * total_qty, 3) if unit_price is not None else None,
                }
            )

        result.sort(key=lambda r: r.get("item_id", ""))
        return result

    @retry_transient()
    def find_on_hand(self) -> list:
        all_rows: list = []
        page_size = 1000
        offset = 0
        while True:
            response = supabase.table("stock").select("*").order("id").range(offset, offset + page_size - 1).execute()
            batch = response.data or []
            all_rows.extend(batch)
            if len(batch) < page_size:
                break
            offset += page_size
        return all_rows

    def create_transfer(
        self,
        from_stock_id: int,
        to_location_id: int,
        quantity: int,
        user_id: int | None = None,
        notes: str | None = None,
    ) -> dict:
        from app.errors import AppError

        try:
            resp = supabase.rpc(
                "transfer_stock",
                {
                    "p_from_stock_id": from_stock_id,
                    "p_to_location_id": to_location_id,
                    "p_quantity": quantity,
                    "p_user_id": user_id,
                    "p_notes": notes,
                },
            ).execute()
            return resp.data
        except Exception as exc:
            msg = str(exc)
            if "not found" in msg:
                raise AppError(404, msg)
            if "Insufficient" in msg or "must be different" in msg:
                raise AppError(400, msg)
            raise

    def create_cross_transfer(
        self,
        from_item_id: int,
        from_location_id: int,
        to_item_id: int,
        to_location_id: int,
        quantity: int,
        user_id: int | None = None,
        notes: str | None = None,
    ) -> dict:
        from datetime import datetime, timezone

        from app.errors import AppError

        from_stock_resp = (
            supabase.table("stock")
            .select("id, quantity")
            .eq("item_id", from_item_id)
            .eq("location_id", from_location_id)
            .limit(1)
            .execute()
        )
        from_stock = from_stock_resp.data[0] if from_stock_resp.data else None
        if not from_stock:
            raise AppError(404, "No stock found for source item at that location")
        if from_stock["quantity"] < quantity:
            raise AppError(
                400,
                f"Insufficient quantity: available {from_stock['quantity']}, requested {quantity}",
            )

        try:
            supabase.table("stock").update({"quantity": from_stock["quantity"] - quantity}).eq(
                "id", from_stock["id"]
            ).execute()

            to_stock_resp = (
                supabase.table("stock")
                .select("id, quantity")
                .eq("item_id", to_item_id)
                .eq("location_id", to_location_id)
                .limit(1)
                .execute()
            )
            existing_to = to_stock_resp.data[0] if to_stock_resp.data else None

            if existing_to:
                to_stock_id = existing_to["id"]
                supabase.table("stock").update({"quantity": existing_to["quantity"] + quantity}).eq(
                    "id", to_stock_id
                ).execute()
            else:
                new_resp = (
                    supabase.table("stock")
                    .insert({"item_id": to_item_id, "location_id": to_location_id, "quantity": quantity})
                    .execute()
                )
                to_stock_id = new_resp.data[0]["id"]

            transfer_data: dict = {
                "stock_id_from_id": from_stock["id"],
                "stock_id_to_id": to_stock_id,
                "quantity": quantity,
                "date": datetime.now(timezone.utc).isoformat(),
                "notes": notes,
                "from_item_id": from_item_id,
                "to_item_id": to_item_id,
            }
            if user_id is not None:
                transfer_data["user_id"] = user_id

            transfer_resp = supabase.table("transfer").insert(transfer_data).execute()
            return transfer_resp.data[0]

        except Exception:
            try:
                current = supabase.table("stock").select("quantity").eq("id", from_stock["id"]).single().execute()
                if current and current.data and current.data["quantity"] != from_stock["quantity"]:
                    supabase.table("stock").update({"quantity": from_stock["quantity"]}).eq(
                        "id", from_stock["id"]
                    ).execute()
            except Exception:
                pass
            raise
