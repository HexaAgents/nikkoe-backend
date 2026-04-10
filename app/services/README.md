# app/services/

Business logic layer. Each service class sits between routers and repositories, converting data-layer results into meaningful errors and orchestrating queries that span multiple repositories. Services are the only layer that raises domain errors like `NotFoundError`.

## How it works

Each service takes one or more repository instances in its constructor and is instantiated at module level in the corresponding router file, so it lives for the lifetime of the application. Most service methods delegate directly to the repository, but add a critical check: if the repository returns `None`, the service raises `NotFoundError` with a descriptive message, which the exception handler converts to an HTTP 404. For complex entities like items, a single service coordinates five repositories to serve the item detail page's data needs.

## Why this design

Services exist to convert repository nulls into meaningful HTTP errors (`NotFoundError` → 404) and to orchestrate multi-repository queries like `ItemService`. Without services, this logic would leak into the router layer.

## Files

- **category.py** -- `CategoryService` wrapping `CategoryRepository` with `list_categories`, `create_category`, and `delete_category`. All three methods are pure delegation with no extra logic.
- **channel.py** -- `ChannelService` with `list_channels` only. Channels are a read-only entity so the service is minimal, delegating directly to the repository.
- **customer.py** -- `CustomerService` with `list_customers` and `create_customer`. Both methods delegate directly to the customer repository.
- **inventory.py** -- `InventoryService` with `list_movements`, `list_on_hand`, `stock_valuation`, `transfer_stock` (same-item location transfer), and `cross_transfer_stock` (cross-item transfer between different part numbers). All delegate to the inventory repository.
- **item.py** -- `ItemService`, the most complex service, whose constructor takes 5 repositories (item, supplier_quote, inventory, receipt, sale) because the item detail page needs data from 5 different tables. Methods: `list_items` (with `sort_by` for server-side sorting), `search_items`, `get_item` (throws `NotFoundError` if null), `get_items_by_search_id` (find items sharing a normalized search ID), `get_item_quotes`, `get_item_inventory`, `get_item_receipts`, `get_item_sales`, `get_item_transfers`, `create_item`, `update_item`, and `delete_item`.
- **location.py** -- `LocationService` with `list_locations`, `create_location`, and `delete_location`. All three methods delegate directly to the location repository.
- **receipt.py** -- `ReceiptService` with `list_receipts`, `get_receipt` (throws `NotFoundError`), `get_receipt_lines`, `create_receipt`, and `void_receipt`. Handles the full receipt lifecycle from listing through voiding.
- **sale.py** -- `SaleService` mirrors `ReceiptService` with `list_sales`, `get_sale`, `get_sale_lines`, `create_sale`, and `void_sale`. `get_sale` throws `NotFoundError` if the sale doesn't exist.
- **supplier.py** -- `SupplierService` with `list_suppliers`, `create_supplier`, and `delete_supplier`. All methods delegate to the supplier repository.
- **supplier_quote.py** -- `SupplierQuoteService` with `create_quote` and `delete_quote`. Both methods delegate directly to the supplier quote repository.
- **user.py** -- `UserService` with `get_profile` (throws `NotFoundError` if profile is `None`) and `create_user` (delegates to the repository's Supabase Auth admin call). Handles user profile retrieval and admin user creation.
