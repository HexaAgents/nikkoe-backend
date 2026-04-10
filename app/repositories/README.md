# app/repositories/

Data access layer. Each repository class encapsulates all Supabase queries for one domain entity and returns raw dicts. Repositories never raise HTTP errors — when a record isn't found, they return `None` and let the service layer decide what that means.

## Database Schema

The database uses PascalCase singular table names with integer primary keys (bigint `id`). Sale and receipt lines link to the `Stock` table (which maps item+location) rather than directly to items and locations. Currency is a separate lookup table.

## Files

- **base.py** -- `batch_load()` utility for efficient relation loading by integer IDs.
- **category.py** -- CRUD against the `Category` table (id, name).
- **channel.py** -- Read-only queries against the `Channel` table (id, name).
- **currency.py** -- Read-only queries against the `Currency` table (id, name).
- **customer.py** -- List/create against the `Customer` table (id, name, email, phone, address fields).
- **inventory.py** -- `Transfer` table for movements, `Stock` table for on-hand balances. `create_transfer` handles same-item location transfers; `create_cross_transfer` handles cross-item transfers between different part numbers with stock quantity updates on both items.
- **item.py** -- CRUD against the `Item` table (id, item_id text, description, category_id, search_id). Stitches Stock, Receipt_Stock, and Category data in memory. `find_by_search_id` returns items sharing a normalized search ID. Auto-generates `search_id` on create/update. Server-side sorting via `get_items_sorted` Postgres RPC for receipt date, sale date, and quantity sorts.
- **location.py** -- CRUD against the `Location` table (id, code).
- **receipt.py** -- `Receipt` + `Receipt_Stock` tables. Multi-step inserts with Stock lookup/creation and quantity increment. Void updates status column.
- **sale.py** -- `Sale` + `Sale_Stock` tables. Multi-step inserts with Stock lookup/creation and quantity decrement. Void updates status column.
- **supplier.py** -- CRUD against the `Supplier` table (id, name, address, email, phone).
- **supplier_quote.py** -- `Item_supplier` table (id, cost, currency_id, item_id, supplier_id, date_time, valid_quote).
- **user.py** -- Creates auth users via `supabase.auth.admin.create_user()`.
