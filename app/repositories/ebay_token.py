from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.dependencies import supabase


class EbayTokenRepository:
    TABLE = "Ebay_Token"

    def get_current(self) -> dict | None:
        resp = supabase.table(self.TABLE).select("*").order("created_at", desc=True).limit(1).execute()
        rows = resp.data or []
        return rows[0] if rows else None

    def upsert(
        self,
        access_token: str,
        refresh_token: str,
        expires_in: int,
        ebay_user_id: str | None = None,
    ) -> dict:
        expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        existing = self.get_current()

        payload = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_expiry": expiry.isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if ebay_user_id:
            payload["ebay_user_id"] = ebay_user_id

        if existing:
            resp = supabase.table(self.TABLE).update(payload).eq("id", existing["id"]).execute()
            return resp.data[0]

        payload["created_at"] = datetime.now(timezone.utc).isoformat()
        resp = supabase.table(self.TABLE).insert(payload).execute()
        return resp.data[0]

    def update_access_token(self, token_id: int, access_token: str, expires_in: int) -> dict:
        expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        resp = (
            supabase.table(self.TABLE)
            .update(
                {
                    "access_token": access_token,
                    "token_expiry": expiry.isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            .eq("id", token_id)
            .execute()
        )
        return resp.data[0]

    def delete_all(self) -> None:
        current = self.get_current()
        if current:
            supabase.table(self.TABLE).delete().eq("id", current["id"]).execute()


class EbaySyncLogRepository:
    TABLE = "Ebay_Sync_Log"

    def create(self, sync_from: str | None = None) -> dict:
        payload: dict = {"status": "RUNNING"}
        if sync_from:
            payload["sync_from"] = sync_from
        resp = supabase.table(self.TABLE).insert(payload).execute()
        return resp.data[0]

    def complete(
        self,
        log_id: int,
        *,
        orders_fetched: int = 0,
        orders_imported: int = 0,
        orders_skipped: int = 0,
        sync_to: str | None = None,
    ) -> dict:
        payload = {
            "status": "SUCCESS",
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "orders_fetched": orders_fetched,
            "orders_imported": orders_imported,
            "orders_skipped": orders_skipped,
        }
        if sync_to:
            payload["sync_to"] = sync_to
        resp = supabase.table(self.TABLE).update(payload).eq("id", log_id).execute()
        return resp.data[0]

    def fail(self, log_id: int, error_message: str) -> dict:
        resp = (
            supabase.table(self.TABLE)
            .update(
                {
                    "status": "FAILED",
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                    "error_message": error_message,
                }
            )
            .eq("id", log_id)
            .execute()
        )
        return resp.data[0]

    def get_last_successful(self) -> dict | None:
        resp = (
            supabase.table(self.TABLE)
            .select("*")
            .eq("status", "SUCCESS")
            .order("finished_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        return rows[0] if rows else None

    def list_recent(self, limit: int = 20) -> list[dict]:
        resp = supabase.table(self.TABLE).select("*").order("started_at", desc=True).limit(limit).execute()
        return resp.data or []
