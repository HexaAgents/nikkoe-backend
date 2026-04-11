# nikkoe-backend

Python/FastAPI REST API for the Nikkoe inventory management platform. It handles authentication, CRUD for inventory entities (items, receipts, sales, suppliers, etc.), and exposes a paginated REST API consumed by the React frontend. The backend uses Supabase for both authentication and Postgres database access.

## How it works

Every request flows through four layers: Router → Service → Repository → Database. The router receives the HTTP request, validates input with Pydantic schemas, and resolves the auth dependency. The service enforces business rules — such as converting a missing record into a `NotFoundError` — and orchestrates queries across multiple repositories when needed. Each repository builds and executes Supabase queries against PascalCase tables (Item, Sale, Receipt, Stock, etc.) with integer primary keys. For sale/receipt creation, the repository performs multi-step inserts: creates the header row, looks up or creates Stock rows for each item+location combination, inserts line items (Sale_Stock/Receipt_Stock), and updates Stock quantities.

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
- `CORS_ORIGINS` -- Comma-separated list of allowed frontend origins (default: `http://localhost:8080`). For production, include the deployed frontend URL e.g. `http://localhost:8080,https://nikkoe-frontend.vercel.app`.

## Project Structure

```
app/
  main.py              FastAPI app -- CORS, router mounting, exception handlers, health endpoint
  config.py            Pydantic Settings loading env vars
  dependencies.py      Supabase client singleton
  errors.py            AppError, NotFoundError, ConflictError, ForbiddenError + exception handlers
  schemas.py           All Pydantic request/response models

  middleware/
    auth.py            JWT auth dependency -- verifies token via Supabase, loads User profile (first_name + last_name)

  repositories/
    base.py            batch_load, paginated_fetch, retry_transient decorator for HTTP/2 resilience
    category.py        CRUD → Category table (id, name)
    channel.py         Read-only → Channel table (id, name)
    currency.py        Read-only → Currency table (id, name)
    customer.py        List/create → Customer table (id, name, email, phone, address)
    inventory.py       Transfer table (movements), Stock table (on-hand balances)
    item.py            CRUD → Item table (id, item_id text, description, category_id)
    location.py        CRUD → Location table (id, code)
    receipt.py         Receipt + Receipt_Stock — multi-step inserts with Stock lookup, quantity increment
    sale.py            Sale + Sale_Stock — multi-step inserts with Stock lookup, quantity decrement
    supplier.py        CRUD → Supplier table (id, name, address, email, phone)
    supplier_quote.py  CRUD → Item_supplier table (id, cost, currency_id, item_id, supplier_id)
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
    auth.py            POST /api/auth/login, /signup, /change-password + GET /api/auth/me
    categories.py      GET/POST/DELETE /api/categories (→ Category table)
    channels.py        GET /api/channels (→ Channel table)
    currencies.py      GET /api/currencies (→ Currency table)
    customers.py       GET/POST /api/customers (→ Customer table)
    inventory.py       GET /api/inventory/movements (→ Transfer), GET /api/inventory/on-hand (→ Stock)
    items.py           9 endpoints for items and sub-resources (→ Item table)
    locations.py       GET/POST/DELETE /api/locations (→ Location table)
    receipts.py        GET/POST /api/receipts, void endpoint (→ Receipt + Receipt_Stock)
    sales.py           GET/POST /api/sales, void endpoint (→ Sale + Sale_Stock)
    suppliers.py       GET/POST/DELETE /api/suppliers (→ Supplier table)
    supplier_quotes.py POST/DELETE /api/supplier-quotes (→ Item_supplier table)
    users.py           GET /api/users/me, POST /api/users (→ User table)

tests/
  conftest.py                Shared fixtures (TestClient, mock users, auth overrides)
  test_health.py         (2) Smoke test — app boots and /api/health responds
  test_schemas.py      (108) Pydantic model validation rules
  test_errors.py        (19) Error classes and exception handlers
  test_services.py      (75) Business logic with mocked repositories
  test_routers.py       (61) HTTP validation (malformed bodies → 422)
  test_router_responses.(117) Happy-path router responses with mocked services
  test_response_contracts(47) Response shape contracts (paginated, array, etc.)
  test_auth_enforcement  (56) Every protected endpoint returns 401 without token
  test_repositories.py   (36) Repository-level tests (upsert, retry, chunking guards)
  test_endpoint_smoke    (16) Every endpoint returns non-500 with mocked services
  test_dependencies.py    (5) Supabase client configuration guards
  test_auth_cache.py      (7) Auth token caching
  test_invoice_parser    (23) Invoice parser unit tests
  test_stock_valuation    (6) Stock valuation logic

docs/
  login-flow.drawio              Step-by-step login authentication flowchart
  create-sale-flow.drawio        Step-by-step sale creation flowchart
  create-receipt-flow.drawio     Step-by-step receipt creation flowchart
  endpoint-flowcharts/           Per-endpoint flowcharts

supabase/
  migrations/          SQL migrations (void/status, auto-increment sequences, item_supplier dedup + unique constraint)
```

## Testing

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest --tb=short -q
```

639 tests across 18 files covering schemas, services, routers, repositories, error handlers, auth enforcement, response contracts, and more. All tests use mocked dependencies — no database or network required. See `tests/README.md` for detailed documentation of every test.
