# nikkoe-backend

Python/FastAPI REST API for the Nikkoe inventory management platform. It handles authentication, CRUD for inventory entities (items, receipts, sales, suppliers, etc.), and exposes a paginated REST API consumed by the React frontend. The backend uses Supabase for both authentication and Postgres database access.

## How it works

Every request flows through four layers: Router → Service → Repository → Database. The router receives the HTTP request, validates input with Pydantic schemas, and resolves the auth dependency. The service enforces business rules — such as converting a missing record into a `NotFoundError` — and orchestrates queries across multiple repositories when needed. Each repository builds and executes Supabase queries for a single domain table, returning raw dicts. For multi-row atomic operations (receipt/sale creation, voiding), the repository calls a Postgres RPC function to ensure all-or-nothing behavior inside a database transaction.

## Why this design

Separating the code into layers (routing, business logic, data access) keeps each layer independently testable and enforces separation of concerns — routers never touch the database, repositories never raise HTTP errors, and services bridge the two.

## Setup

1. **Copy the environment template** and fill in your Supabase credentials (find the service role key under Supabase Dashboard > Settings > API):
   ```bash
   cp .env.example .env
   ```

2. **Create and activate a virtual environment** so dependencies are isolated from the system Python:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Start the dev server** (auto-reloads on file changes):
   ```bash
   uvicorn app.main:app --reload --port 3000
   ```

The server starts on `http://localhost:3000`. All routes are under `/api/`. Interactive Swagger docs are at `http://localhost:3000/docs`.

## Environment Variables

- `SUPABASE_URL` -- Supabase project URL.
- `SUPABASE_SERVICE_ROLE_KEY` -- Service role key (server-side only, never expose to the client).
- `SUPABASE_ANON_KEY` -- Anon/publishable key.
- `PORT` -- Server port (default: 3000).
- `CORS_ORIGIN` -- Allowed frontend origin (default: `http://localhost:8080`).

## Project Structure

```
app/
  main.py              FastAPI app -- CORS, router mounting, exception handlers, health endpoint
  config.py            Pydantic Settings loading env vars
  dependencies.py      Supabase client singleton
  errors.py            AppError, NotFoundError, ConflictError, ForbiddenError + exception handlers
  schemas.py           All Pydantic request/response models

  middleware/
    auth.py            JWT auth dependency -- verifies token via Supabase, attaches user to request

  repositories/
    base.py            batch_load utility for efficient relation loading
    category.py        Category CRUD queries
    channel.py         Channel read-only queries
    customer.py        Customer queries
    inventory.py       Inventory movements and balances with relation stitching
    item.py            Item queries with multi-table relation assembly
    location.py        Location CRUD queries
    receipt.py         Receipt queries, atomic creation via RPC, voiding via RPC
    sale.py            Sale queries, atomic creation via RPC, voiding via RPC
    supplier.py        Supplier CRUD queries
    supplier_quote.py  Supplier quote queries
    user.py            User creation via Supabase Auth admin API

  services/
    category.py        Category business logic
    channel.py         Channel business logic
    customer.py        Customer business logic
    inventory.py       Inventory business logic
    item.py            Item business logic (takes 5 repositories for cross-domain queries)
    location.py        Location business logic
    receipt.py         Receipt business logic with NotFoundError handling
    sale.py            Sale business logic with NotFoundError handling
    supplier.py        Supplier business logic
    supplier_quote.py  Supplier quote business logic
    user.py            User profile and creation logic

  routers/
    auth.py            POST /api/auth/login, /signup, /change-password
    categories.py      GET/POST/DELETE /api/categories
    channels.py        GET /api/channels
    customers.py       GET/POST /api/customers
    inventory.py       GET /api/inventory/movements, GET /api/inventory/on-hand
    items.py           9 endpoints for items and sub-resources
    locations.py       GET/POST/DELETE /api/locations
    receipts.py        GET/POST /api/receipts, void endpoint
    sales.py           GET/POST /api/sales, void endpoint
    suppliers.py       GET/POST/DELETE /api/suppliers
    supplier_quotes.py POST/DELETE /api/supplier-quotes
    users.py           GET /api/users/me, POST /api/users

supabase/
  migrations/          SQL migrations (atomic receipt/sale creation RPCs)
```
