from app.dependencies import supabase
from app.repositories.base import batch_load


class ReceiptRepository:
    def find_all(self, limit: int = 50, offset: int = 0) -> dict:
        response = (
            supabase.table("receipts")
            .select("*", count="exact")
            .order("received_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        receipts = response.data or []
        total = response.count or 0

        supplier_ids = list({r["supplier_id"] for r in receipts if r.get("supplier_id")})
        user_ids = list({r["user_id"] for r in receipts if r.get("user_id")})

        suppliers_map = batch_load("suppliers", "supplier_id", supplier_ids)
        users_map = batch_load("users", "user_id", user_ids)

        for r in receipts:
            r["suppliers"] = suppliers_map.get(r.get("supplier_id"))
            r["users"] = users_map.get(r.get("user_id"))

        return {"data": receipts, "total": total}

    def find_by_id(self, id: str) -> dict | None:
        response = supabase.table("receipts").select("*").eq("receipt_id", id).maybe_single().execute()
        receipt = response.data
        if not receipt:
            return None

        if receipt.get("supplier_id"):
            sup_resp = (
                supabase.table("suppliers")
                .select("*")
                .eq("supplier_id", receipt["supplier_id"])
                .maybe_single()
                .execute()
            )
            receipt["suppliers"] = sup_resp.data

        if receipt.get("user_id"):
            usr_resp = supabase.table("users").select("*").eq("user_id", receipt["user_id"]).maybe_single().execute()
            receipt["users"] = usr_resp.data

        return receipt

    def find_lines(self, receipt_id: str) -> list:
        response = (
            supabase.table("receipt_lines").select("*").eq("receipt_id", receipt_id).order("created_at").execute()
        )
        return response.data or []

    def find_by_item_id(self, item_id: str) -> list:
        response = (
            supabase.table("receipt_lines")
            .select("*, receipts(receipt_id, received_at, suppliers(supplier_name)), locations(location_code)")
            .eq("item_id", item_id)
            .order("created_at", desc=True)
            .execute()
        )
        return response.data or []

    def create(self, receipt: dict, lines: list[dict]) -> dict:
        response = supabase.rpc("create_receipt", {"p_receipt": receipt, "p_lines": lines}).execute()
        return response.data

    def void_receipt(self, receipt_id: str, user_id: str, reason: str) -> None:
        supabase.rpc(
            "void_receipt",
            {"p_receipt_id": receipt_id, "p_user_id": user_id, "p_reason": reason},
        ).execute()
