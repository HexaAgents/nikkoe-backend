# app/repositories/

Data access layer. Each repository class encapsulates all Supabase queries for one domain entity and returns raw dicts. Repositories never raise HTTP errors — when a record isn't found, they return `None` and let the service layer decide what that means.

## How it works

Each repository class targets a single database table and provides methods like `find_all`, `create`, and `remove`. For list queries that reference related data (e.g. receipts referencing suppliers), repositories use the `batch_load` utility to fetch all related rows in a single query and stitch them together in memory, avoiding N+1 queries. For atomic multi-row operations like receipt/sale creation and voiding, repositories call Postgres RPC functions instead of individual REST queries, ensuring all-or-nothing transactional behavior.

## Why this design

Repositories return raw dicts because the Supabase Python client returns dicts natively — converting to Pydantic models at this layer would add overhead with no benefit since response serialization happens at the router level.

## Files

- **base.py** -- Contains `batch_load()`, a generic utility that fetches multiple rows by a list of IDs in a single Supabase query and returns them as a `dict[str, dict]` for O(1) lookup. Used by item, receipt, sale, and inventory repositories to efficiently load related data without N+1 queries.
- **category.py** -- `CategoryRepository` with `find_all(limit, offset)` (paginated SELECT ordered by name), `create(data)` (INSERT returning new row), and `remove(id)` (DELETE by category_id). Provides standard CRUD operations against the `categories` table.
- **channel.py** -- `ChannelRepository` with `find_all(limit, offset)` only. Channels are read-only reference data managed outside the application, so no create or delete methods are needed.
- **customer.py** -- `CustomerRepository` with `find_all(limit, offset)` and `create(data)`. Note that the database table is named `customer` (singular), not `customers`.
- **inventory.py** -- `InventoryRepository` with `find_movements(limit, offset)` (paginated movements with batch-loaded item/user relations), `find_by_item_id(item_id)` (balances for a specific item with location joins), and `find_on_hand()` (all positive stock balances). All three methods handle the PGRST205 error for the `inventory_balances` database view.
- **item.py** -- `ItemRepository`, the most complex repository. `find_all` runs 5 separate queries — items, categories, inventory_balances, receipt_lines, locations, and receipts — then stitches them together in memory using Maps. Also provides `find_by_id` (with categories join), `create`, `update`, and `remove`.
- **location.py** -- `LocationRepository` with `find_all`, `create`, and `remove` against the `locations` table. Provides standard CRUD operations for warehouse and storage locations.
- **receipt.py** -- `ReceiptRepository` with `find_all` (batch-loads suppliers and users), `find_by_id` (loads supplier and user individually), `find_lines`, `find_by_item_id`, `create` (calls `create_receipt` RPC for atomic insertion), and `void_receipt` (calls `void_receipt` RPC). Handles the full lifecycle of purchase receipts from creation through voiding.
- **sale.py** -- `SaleRepository` mirrors the receipt repository. `find_all` batch-loads channels and users, `create` calls `create_sale` RPC, and `void_sale` calls `void_sale` RPC.
- **supplier.py** -- `SupplierRepository` with `find_all`, `create`, and `remove` against the `suppliers` table. Provides standard CRUD operations for supplier records.
- **supplier_quote.py** -- `SupplierQuoteRepository` with `find_by_item_id` (quotes with supplier names via join), `create`, and `remove`. Manages price quotes that suppliers offer for specific items.
- **user.py** -- `UserRepository` with `create_auth_user(email, password)` which calls `supabase.auth.admin.create_user()` to register a user in Supabase Auth. This is the only repository that interacts with Supabase Auth rather than a database table.
