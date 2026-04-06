from datetime import datetime, timezone

from dotenv import load_dotenv as _load_dotenv

_load_dotenv()

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from app.config import settings  # noqa: E402
from app.errors import AppError, app_error_handler, general_error_handler, validation_error_handler  # noqa: E402
from app.routers import (  # noqa: E402
    auth,
    categories,
    channels,
    currencies,
    customers,
    inventory,
    items,
    locations,
    receipts,
    sales,
    supplier_quotes,
    suppliers,
    users,
)

app = FastAPI(title="nikkoe-backend")

allow_origin_regex = r"https://.*\.vercel\.app"
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",")],
    allow_origin_regex=allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(ValidationError, validation_error_handler)
app.add_exception_handler(Exception, general_error_handler)

app.include_router(auth.router)
app.include_router(receipts.router)
app.include_router(sales.router)
app.include_router(items.router)
app.include_router(suppliers.router)
app.include_router(locations.router)
app.include_router(categories.router)
app.include_router(channels.router)
app.include_router(customers.router)
app.include_router(inventory.router)
app.include_router(users.router)
app.include_router(supplier_quotes.router)
app.include_router(currencies.router)

if settings.EBAY_CLIENT_ID:
    from app.routers import ebay  # noqa: E402

    app.include_router(ebay.router)


@app.on_event("startup")
def startup_event():
    if settings.EBAY_CLIENT_ID:
        from app.ebay.scheduler import start_scheduler

        start_scheduler()


@app.on_event("shutdown")
def shutdown_event():
    if settings.EBAY_CLIENT_ID:
        from app.ebay.scheduler import stop_scheduler

        stop_scheduler()


@app.get("/api/health")
def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}
