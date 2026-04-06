from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _run_sync() -> None:
    from app.services.ebay_sync import EbaySyncService

    try:
        service = EbaySyncService()
        result = service.sync_orders()
        logger.info("eBay scheduled sync completed: %s", result)
    except Exception:
        logger.exception("eBay scheduled sync failed")


def start_scheduler() -> None:
    global _scheduler

    if not settings.EBAY_CLIENT_ID:
        logger.info("eBay credentials not configured — scheduler not started")
        return

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        _run_sync,
        "interval",
        minutes=settings.EBAY_SYNC_INTERVAL_MINUTES,
        id="ebay_sync",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info(
        "eBay sync scheduler started (every %d minutes)",
        settings.EBAY_SYNC_INTERVAL_MINUTES,
    )


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("eBay sync scheduler stopped")
