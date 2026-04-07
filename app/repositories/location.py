from app.dependencies import supabase

PAGE_SIZE = 1000


class LocationRepository:
    def find_all(self, limit: int = 5000, offset: int = 0, search: str | None = None) -> dict:
        all_data: list = []
        total = 0
        current_offset = offset
        remaining = limit

        while remaining > 0:
            batch = min(remaining, PAGE_SIZE)
            query = supabase.table("location").select("*", count="exact").order("code")
            if search:
                query = query.ilike("code", f"%{search}%")
            response = query.range(current_offset, current_offset + batch - 1).execute()
            rows = response.data or []
            if total == 0:
                total = response.count or 0
            all_data.extend(rows)
            if len(rows) < batch:
                break
            current_offset += batch
            remaining -= batch

        location_ids = [loc["id"] for loc in all_data]
        stock_summary = self._get_stock_summary(location_ids)
        for loc in all_data:
            summary = stock_summary.get(loc["id"], {})
            loc["total_quantity"] = summary.get("total_quantity", 0)
            loc["part_count"] = summary.get("part_count", 0)

        return {"data": all_data, "total": total}

    def _get_stock_summary(self, location_ids: list[int]) -> dict:
        if not location_ids:
            return {}

        summary: dict[int, dict] = {}
        offset = 0
        while True:
            response = (
                supabase.table("stock")
                .select("location_id, item_id, quantity")
                .gt("quantity", 0)
                .range(offset, offset + PAGE_SIZE - 1)
                .execute()
            )
            rows = response.data or []
            for row in rows:
                loc_id = row["location_id"]
                if loc_id not in summary:
                    summary[loc_id] = {"total_quantity": 0, "items": set()}
                summary[loc_id]["total_quantity"] += row.get("quantity", 0)
                summary[loc_id]["items"].add(row["item_id"])
            if len(rows) < PAGE_SIZE:
                break
            offset += PAGE_SIZE

        return {
            loc_id: {
                "total_quantity": info["total_quantity"],
                "part_count": len(info["items"]),
            }
            for loc_id, info in summary.items()
        }

    def find_by_id(self, id: int) -> dict | None:
        response = supabase.table("location").select("*").eq("id", id).maybe_single().execute()
        return response.data

    def find_items_by_location(self, location_id: int) -> list:
        response = (
            supabase.table("stock")
            .select("id, quantity, item_id, item(id, item_id, description, category(name))")
            .eq("location_id", location_id)
            .gt("quantity", 0)
            .execute()
        )
        rows = response.data or []
        if not rows:
            return []

        stock_ids = [r["id"] for r in rows]
        stock_item_map = {r["id"]: r["item_id"] for r in rows}

        receipt_lines: list = []
        for i in range(0, len(stock_ids), PAGE_SIZE):
            batch = stock_ids[i : i + PAGE_SIZE]
            resp = (
                supabase.table("receipt_stock")
                .select("stock_id, unit_price, receipt(dateTime, status)")
                .in_("stock_id", batch)
                .execute()
            )
            receipt_lines.extend(resp.data or [])

        item_price_map: dict[int, dict] = {}
        for rl in receipt_lines:
            receipt = rl.get("receipt") or {}
            if receipt.get("status") == "VOIDED":
                continue
            item_id = stock_item_map.get(rl.get("stock_id"))
            if item_id is None:
                continue
            date = receipt.get("dateTime", "")
            existing = item_price_map.get(item_id)
            if not existing or date > existing["date"]:
                item_price_map[item_id] = {"date": date, "unit_price": rl.get("unit_price")}

        result = []
        for row in rows:
            item = row.get("item") or {}
            cat = item.pop("category", None)
            price_info = item_price_map.get(row["item_id"])
            result.append(
                {
                    "id": item.get("id"),
                    "item_id": item.get("item_id", ""),
                    "description": item.get("description"),
                    "category": cat.get("name") if cat else None,
                    "quantity": row.get("quantity", 0),
                    "last_unit_price": price_info["unit_price"] if price_info else None,
                }
            )

        result.sort(key=lambda r: r.get("item_id", ""))
        return result

    def create(self, data: dict) -> dict:
        response = supabase.table("location").insert(data).execute()
        return response.data[0]

    def remove(self, id: int) -> None:
        supabase.table("location").delete().eq("id", id).execute()
