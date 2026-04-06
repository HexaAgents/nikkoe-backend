from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.dependencies import supabase
from app.ebay import client as ebay_client
from app.middleware.auth import CurrentUser, get_current_user
from app.repositories.ebay_token import EbaySyncLogRepository, EbayTokenRepository
from app.services.ebay_sync import SOURCE_TAG, EbaySyncService

router = APIRouter(prefix="/api/ebay", tags=["ebay"])

token_repo = EbayTokenRepository()
sync_log_repo = EbaySyncLogRepository()
sync_service = EbaySyncService(token_repo, sync_log_repo)


@router.get("/auth")
def ebay_auth(user: CurrentUser = Depends(get_current_user)):
    """Redirect to eBay OAuth consent screen."""
    url = ebay_client.get_consent_url()
    return {"consent_url": url}


@router.get("/callback")
def ebay_callback(code: str = Query(...)):
    """Handle eBay OAuth callback — exchange authorization code for tokens."""
    try:
        result = ebay_client.exchange_code_for_token(code)
        token_repo.upsert(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            expires_in=result["expires_in"],
        )
        return {"message": "eBay account linked successfully"}
    except Exception as exc:
        return JSONResponse(status_code=400, content={"error": f"Token exchange failed: {exc}"})


@router.post("/token")
def ebay_manual_token(code: str = Query(...), user: CurrentUser = Depends(get_current_user)):
    """Manually exchange an authorization code (for sandbox where redirect doesn't work)."""
    try:
        result = ebay_client.exchange_code_for_token(code)
        token_repo.upsert(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            expires_in=result["expires_in"],
        )
        return {"message": "eBay account linked successfully"}
    except Exception as exc:
        return JSONResponse(status_code=400, content={"error": f"Token exchange failed: {exc}"})


@router.get("/status")
def ebay_status(user: CurrentUser = Depends(get_current_user)):
    """Return current eBay connection status and last sync info."""
    stored = token_repo.get_current()
    last_sync = sync_log_repo.get_last_successful()

    if not stored:
        return {
            "linked": False,
            "last_sync": None,
        }

    return {
        "linked": True,
        "ebay_user_id": stored.get("ebay_user_id"),
        "token_expiry": stored.get("token_expiry"),
        "last_sync": last_sync,
    }


@router.post("/sync")
def trigger_sync(
    date_from: str | None = Query(default=None),
    user: CurrentUser = Depends(get_current_user),
):
    """Trigger a manual eBay order sync."""
    result = sync_service.sync_orders(date_from=date_from)
    return result


@router.get("/sync/history")
def sync_history(
    limit: int = Query(default=20, ge=1, le=100),
    user: CurrentUser = Depends(get_current_user),
):
    """List recent sync log entries."""
    return sync_log_repo.list_recent(limit)


@router.get("/purge/preview")
def purge_preview(user: CurrentUser = Depends(get_current_user)):
    """Preview counts of eBay-imported records that would be deleted."""
    tables = ["Sale_Stock", "Sale", "Stock", "Item", "Customer"]
    counts = {}
    for table in tables:
        resp = supabase.table(table).select("id", count="exact").eq("source", SOURCE_TAG).limit(0).execute()
        counts[table] = resp.count or 0
    return {"counts": counts, "source": SOURCE_TAG}


@router.delete("/purge")
def purge_ebay_data(user: CurrentUser = Depends(get_current_user)):
    """Delete ALL eBay-imported data (source = EBAY_IMPORT) in FK-safe order."""
    tables = ["Sale_Stock", "Sale", "Stock", "Item", "Customer"]
    deleted = {}
    for table in tables:
        resp = supabase.table(table).select("id", count="exact").eq("source", SOURCE_TAG).limit(0).execute()
        count = resp.count or 0
        if count > 0:
            supabase.table(table).delete().eq("source", SOURCE_TAG).execute()
        deleted[table] = count

    token_repo.delete_all()
    deleted["Ebay_Token"] = 1

    return {"deleted": deleted, "message": "All eBay-imported data has been purged"}
