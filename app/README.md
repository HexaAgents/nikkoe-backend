# app/

Root package of the FastAPI backend application. Everything the server needs — configuration, error handling, data access, business logic, and HTTP routing — lives under this package. Subfolders separate concerns into middleware, repositories, services, and routers.

## How it works

When Uvicorn starts, it loads `main.py` which creates the FastAPI app instance, configures CORS, registers exception handlers, and mounts all 12 routers. Configuration is validated at startup via Pydantic Settings in `config.py`, so missing environment variables cause an immediate clear error rather than a cryptic runtime failure. A singleton Supabase client is created in `dependencies.py` and shared by every repository. Request and response shapes are defined once in `schemas.py` using Pydantic models, which handle both input validation and response serialization.

## Why this design

A single `schemas.py` replaces what would be separate Zod schemas and TypeScript interfaces in Node.js — Pydantic handles both validation and typing in one place, so every model is defined once and used for parsing, type safety, and documentation.

## Files

- **main.py** -- Entry point loaded by Uvicorn (`app.main:app`). Creates the FastAPI app, configures CORS to allow the frontend origin, registers exception handlers for `AppError`/`ValidationError`/general errors, mounts all 12 routers, and defines the `/api/health` endpoint.
- **config.py** -- Uses Pydantic Settings to load environment variables from `.env`. Validates at startup that required vars (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`) are present, failing immediately if missing rather than crashing at runtime.
- **dependencies.py** -- Creates two singleton Supabase clients using the service role key: `supabase` (used by all repositories for data access) and `supabase_auth` (used for auth operations). Uses the default `create_client` configuration — a custom httpx client is intentionally avoided because it caused "Illegal header" errors on Vercel serverless. HTTP/2 connection resilience is handled instead by the `retry_transient` decorator in `repositories/base.py`.
- **errors.py** -- Defines `AppError` (base class with status_code), `NotFoundError` (404), `ConflictError` (409), and `ForbiddenError` (403). Also contains FastAPI exception handlers that catch these plus Pydantic `ValidationError` (400) and PostgreSQL errors (23505→409, 23503→409, 23502→400).
- **schemas.py** -- All Pydantic models for request validation and response serialization. Includes `PaginationParams`, `PaginatedResult[T]`, input models for every entity (`CategoryInput`, `SaleInput`, etc.), composite request models (`CreateSaleRequest` with nested lines), and auth models (`LoginInput`, `SignupInput`, `ChangePasswordInput`).
