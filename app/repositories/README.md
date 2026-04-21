# app/repositories/

Data access layer. Each repository class encapsulates all Supabase queries for one domain entity and returns raw dicts. Repositories never raise HTTP errors — when a record isn't found, they return `None` and let the service layer decide what that means. All read methods are decorated with `@retry_transient()` from `base.py`, which automatically retries on transient HTTP/2 connection errors (GOAWAY frames, socket exhaustion) that occur when the frontend fires many concurrent requests.

## Database Schema

The database uses lowercase singular table names with integer primary keys (bigint `id`). Sale and receipt lines link to the `stock` table (which maps item+location via a `UNIQUE(item_id, location_id)` constraint) rather than directly to items and locations. Currency is a separate lookup table. Stock valuation is computed via the `v_stock_valuation` SQL view.

## Files

- **base.py** -- Shared utilities: `batch_load()` and `batch_in_load()` for chunked relation loading by integer IDs (avoids PostgREST URL length limits), `paginated_fetch()` for paging through the 1000-row PostgREST ceiling, `dash_insensitive_pattern()` for part-number search, and `retry_transient()` decorator that retries repository methods on transient HTTP/2 connection errors (GOAWAY, socket exhaustion) with configurable backoff.
- **category.py** -- CRUD against the `Category` table (id, name).
- **channel.py** -- Read-only queries against the `Channel` table (id, name).
- **currency.py** -- Read-only queries against the `Currency` table (id, name).
- **customer.py** -- List/create against the `Customer` table (id, name, email, phone, address fields).
- **inventory.py** -- `Transfer` table for movements, `Stock` table for on-hand balances. `create_transfer` delegates to the `transfer_stock` Postgres RPC for atomic same-item transfers; `create_cross_transfer` handles cross-item transfers between different part numbers. `stock_valuation` queries the `v_stock_valuation` SQL view. All read methods use `@retry_transient()` for HTTP/2 resilience.
- **item.py** -- CRUD against the `Item` table (id, item_id text, description, category_id, search_id). Stitches Stock, Receipt_Stock, and Category data in memory. `find_by_search_id` returns items sharing a normalized search ID. Auto-generates `search_id` on create/update. Server-side sorting via `get_items_sorted` Postgres RPC for receipt date, sale date, and quantity sorts.
- **location.py** -- CRUD against the `Location` table (id, code). `find_all` enriches locations with stock summaries using chunked `.in_()` queries (batches of 300) to avoid PostgREST URL length limits. All read methods use `@retry_transient()`.
- **receipt.py** -- `Receipt` + `Receipt_Stock` tables. Uses `create_receipt_tx` Postgres RPC for atomic creation with stock quantity increment. Uses `void_receipt_tx` RPC for atomic voiding with stock quantity restoration.
- **sale.py** -- `Sale` + `Sale_Stock` tables. Uses `create_sale_tx` Postgres RPC for atomic creation with stock quantity decrement. Uses `void_sale_tx` RPC for atomic voiding with stock quantity restoration.
- **supplier.py** -- CRUD against the `Supplier` table (id, name, address, email, phone).
- **supplier_quote.py** -- `Item_supplier` table (id, cost, currency_id, item_id, supplier_id, date_time, note). `create` uses Postgres upsert via `ON CONFLICT(item_id, supplier_id)` for atomic create-or-update in a single round-trip. Errors are wrapped in `AppError` for clean API responses. Read method uses `@retry_transient()`.
- **user.py** -- Creates auth users via `supabase.auth.admin.create_user()`.
