# Endpoint Flowcharts

Visual trace maps for every API endpoint in the Nikkoe platform. Each flowchart shows the complete request path from the frontend hook through the backend router, service, and repository layers to the database operation, with exact file locations and line numbers.

## How to read the flowcharts

Each diagram uses colour-coded arrows to show where data crosses system boundaries:

- **Orange arrows** -- Frontend communicating with the Backend (HTTP request)
- **Blue arrows** -- Backend communicating with the Database (Supabase query or RPC)
- **Purple arrows** -- Backend communicating with Supabase Auth (authentication operations)

Every node shows `[C]` for where a function is called and `[D]` for where it is defined, with full file paths from the repo root. A plain-English description below each endpoint title explains what the endpoint does in non-technical terms.

## View online (no IDE needed)

Click any link below to open the flowchart in the draw.io web viewer:

- [Auth Endpoints (3)](https://app.diagrams.net/?url=https://raw.githubusercontent.com/HexaAgents/nikkoe-backend/main/docs/endpoint-flowcharts/auth-endpoints.drawio) -- Login, Signup, Change Password
- [Sales Endpoints (5)](https://app.diagrams.net/?url=https://raw.githubusercontent.com/HexaAgents/nikkoe-backend/main/docs/endpoint-flowcharts/sales-endpoints.drawio) -- List, Get, Lines, Create, Void
- [Receipt Endpoints (5)](https://app.diagrams.net/?url=https://raw.githubusercontent.com/HexaAgents/nikkoe-backend/main/docs/endpoint-flowcharts/receipt-endpoints.drawio) -- List, Get, Lines, Create, Void
- [Item Endpoints (9)](https://app.diagrams.net/?url=https://raw.githubusercontent.com/HexaAgents/nikkoe-backend/main/docs/endpoint-flowcharts/item-endpoints.drawio) -- CRUD + Quotes, Inventory, Receipts, Sales sub-resources
- [Category, Supplier & Location Endpoints (9)](https://app.diagrams.net/?url=https://raw.githubusercontent.com/HexaAgents/nikkoe-backend/main/docs/endpoint-flowcharts/category-supplier-location-endpoints.drawio) -- GET, POST, DELETE for each
- [Channel, Customer & Quote Endpoints (5)](https://app.diagrams.net/?url=https://raw.githubusercontent.com/HexaAgents/nikkoe-backend/main/docs/endpoint-flowcharts/channel-customer-quote-endpoints.drawio) -- Channels (read-only), Customers, Supplier Quotes
- [Inventory, User & Health Endpoints (5)](https://app.diagrams.net/?url=https://raw.githubusercontent.com/HexaAgents/nikkoe-backend/main/docs/endpoint-flowcharts/inventory-user-health-endpoints.drawio) -- Movements, On-hand, Users, Health

## Files

- **auth-endpoints.drawio** -- 3 endpoints covering login, signup, and password change. All route through the backend to Supabase Auth (purple arrows). Login and signup are public; change-password requires a JWT.
- **sales-endpoints.drawio** -- 5 endpoints for the sales domain. Create and void use PostgreSQL RPCs for atomic operations that also trigger inventory movements.
- **receipt-endpoints.drawio** -- 5 endpoints mirroring the sales pattern for goods receipts. Same atomic RPC approach for creation and voiding.
- **item-endpoints.drawio** -- 9 endpoints including standard CRUD plus 4 sub-resource queries. The sub-resources delegate to other domain repositories (SupplierQuoteRepo, InventoryRepo, ReceiptRepo, SaleRepo) via the ItemService.
- **category-supplier-location-endpoints.drawio** -- 9 simple CRUD endpoints (3 per entity) for reference data used by items, receipts, and sales.
- **channel-customer-quote-endpoints.drawio** -- 5 endpoints for channels (read-only), customers, and supplier quotes.
- **inventory-user-health-endpoints.drawio** -- 5 endpoints covering inventory movement logs, on-hand balances, user profile, user creation (via Supabase Auth admin), and the public health check.
