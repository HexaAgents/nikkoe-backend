from app.dependencies import supabase
from app.repositories.base import batch_load, dash_insensitive_pattern, paginated_fetch


class InventoryRepository:
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
            supabase.table("transfer")
            .select("*", count="exact")
            .in_("id", list(matching_ids))
            .order("date", desc=True)
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

    def find_by_item_id(self, item_id: int) -> list:
        response = supabase.table("stock").select("*, location(code)").eq("item_id", item_id).execute()
        return response.data or []

    def find_transfers_by_item_id(self, item_id: int) -> list:
        stock_resp = supabase.table("stock").select("id, location_id").eq("item_id", item_id).execute()
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
            extra = batch_load("stock", "id", missing_ids, "id, location_id")
            stocks_map.update(extra)

        location_ids = list({s.get("location_id") for s in stocks_map.values() if s.get("location_id")})
        locations_map = batch_load("location", "id", location_ids, "id, code")

        user_ids = list({t["user_id"] for t in transfers if t.get("user_id")})
        users_map = batch_load("user", "id", user_ids, "id, first_name, last_name")

        result = []
        for t in transfers:
            from_stock = stocks_map.get(t.get("stock_id_from_id"), {})
            to_stock = stocks_map.get(t.get("stock_id_to_id"), {})
            result.append(
                {
                    "id": t["id"],
                    "quantity": t.get("quantity"),
                    "date": t.get("date"),
                    "notes": t.get("notes"),
                    "from_location": locations_map.get(from_stock.get("location_id")),
                    "to_location": locations_map.get(to_stock.get("location_id")),
                    "users": users_map.get(t.get("user_id")),
                }
            )

        result.sort(key=lambda r: r.get("date") or "", reverse=True)
        return result

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
        from datetime import datetime, timezone

        from app.errors import AppError

        # --- Phase 1: read & validate (no mutations) ---
        from_stock_resp = supabase.table("stock").select("*").eq("id", from_stock_id).single().execute()
        from_stock = from_stock_resp.data
        if not from_stock:
            raise AppError(404, f"Source stock row {from_stock_id} not found")

        if from_stock["quantity"] < quantity:
            raise AppError(
                400,
                f"Insufficient quantity: available {from_stock['quantity']}, requested {quantity}",
            )

        if from_stock["location_id"] == to_location_id:
            raise AppError(400, "Source and destination locations must be different")

        loc_resp = supabase.table("location").select("id").eq("id", to_location_id).execute()
        if not loc_resp.data:
            raise AppError(404, f"Destination location {to_location_id} not found")

        to_stock_resp = (
            supabase.table("stock")
            .select("id, quantity")
            .eq("item_id", from_stock["item_id"])
            .eq("location_id", to_location_id)
            .execute()
        )
        existing_to_stock = to_stock_resp.data[0] if to_stock_resp.data else None

        # --- Phase 2: write (all mutations together) ---
        try:
            if existing_to_stock:
                to_stock_id = existing_to_stock["id"]
                supabase.table("stock").update({"quantity": existing_to_stock["quantity"] + quantity}).eq(
                    "id", to_stock_id
                ).execute()
            else:
                new_stock_resp = (
                    supabase.table("stock")
                    .insert({"item_id": from_stock["item_id"], "location_id": to_location_id, "quantity": quantity})
                    .execute()
                )
                to_stock_id = new_stock_resp.data[0]["id"]

            supabase.table("stock").update({"quantity": from_stock["quantity"] - quantity}).eq(
                "id", from_stock_id
            ).execute()

            transfer_data = {
                "stock_id_from_id": from_stock_id,
                "stock_id_to_id": to_stock_id,
                "quantity": quantity,
                "date": datetime.now(timezone.utc).isoformat(),
                "notes": notes,
            }
            if user_id is not None:
                transfer_data["user_id"] = user_id

            transfer_resp = supabase.table("transfer").insert(transfer_data).execute()
            return transfer_resp.data[0]

        except Exception:
            # Best-effort rollback: re-read current state and try to undo
            try:
                current = supabase.table("stock").select("quantity").eq("id", from_stock_id).single().execute()
                if current and current.data and current.data["quantity"] != from_stock["quantity"]:
                    supabase.table("stock").update({"quantity": from_stock["quantity"]}).eq(
                        "id", from_stock_id
                    ).execute()
            except Exception:
                pass
            raise
