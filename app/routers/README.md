# app/routers/

HTTP layer. Each file defines a `fastapi.APIRouter` with endpoints for one domain entity. Routers handle input parsing, auth injection, and response serialization — no business logic lives here.

## How it works

1. FastAPI matches the incoming request to a route by path and HTTP method.
2. Pydantic validates path parameters, query parameters, and request bodies against schemas defined in `app.schemas`, rejecting invalid input with a 400.
3. For protected endpoints, `Depends(get_current_user)` runs the JWT verification flow and attaches the authenticated user.
4. The handler calls the corresponding service method with the validated data and returns the result, which FastAPI serializes as JSON.

## Why this design

Routers are intentionally thin — they parse HTTP, validate via Pydantic, inject the auth dependency, call the service, and return the result. Keeping business logic out of routers makes them easy to test and prevents duplication.

## Files

- **auth.py** -- Auth router at `/api/auth` with three endpoints: `POST /login` (authenticates via Supabase, returns JWT), `POST /signup` (creates account), and `POST /change-password` (requires JWT, verifies current password then updates). Login and signup are public; change-password requires authentication.
- **categories.py** -- Categories router at `/api/categories` with three endpoints: `GET /` (paginated list), `POST /` (create), and `DELETE /{id}` (delete). All endpoints require authentication.
- **channels.py** -- Channels router at `/api/channels` with a single endpoint: `GET /` returns a paginated list. Channels are read-only reference data so no mutation endpoints exist.
- **customers.py** -- Customers router at `/api/customers` with two endpoints: `GET /` (paginated list) and `POST /` (create). Both endpoints require authentication.
- **inventory.py** -- Inventory router at `/api/inventory` with two endpoints: `GET /movements` (paginated with item/user relations) and `GET /on-hand` (all positive balances, not paginated). Both are read-only query endpoints.
- **items.py** -- Items router at `/api/items` with nine endpoints: CRUD (`GET /`, `GET /{id}`, `POST /`, `PUT /{id}`, `DELETE /{id}`) plus four sub-resource queries (`GET /{id}/quotes`, `GET /{id}/inventory`, `GET /{id}/receipts`, `GET /{id}/sales`). Instantiates 5 repositories at module level to serve the item detail page.
- **locations.py** -- Locations router at `/api/locations` with three endpoints: `GET /` (paginated list), `POST /` (create), and `DELETE /{id}` (delete). All endpoints require authentication.
- **receipts.py** -- Receipts router at `/api/receipts` with five endpoints: `GET /`, `GET /{id}`, `GET /{id}/lines`, `POST /`, and `POST /{id}/void`. The void endpoint includes a `ForbiddenError` guard that checks the user has a profile before allowing the operation.
- **sales.py** -- Sales router at `/api/sales` with five endpoints mirroring receipts: `GET /`, `GET /{id}`, `GET /{id}/lines`, `POST /`, and `POST /{id}/void`. The void endpoint also has the `ForbiddenError` guard requiring a user profile.
- **suppliers.py** -- Suppliers router at `/api/suppliers` with three endpoints: `GET /` (paginated list), `POST /` (create), and `DELETE /{id}` (delete). All endpoints require authentication.
- **supplier_quotes.py** -- Supplier quotes router at `/api/supplier-quotes` with two endpoints: `POST /` (create a new quote) and `DELETE /{id}` (delete an existing quote). Both endpoints require authentication.
- **users.py** -- Users router at `/api/users` with two endpoints: `GET /me` (returns the current user's profile) and `POST /` (admin create user via Supabase Auth). Both endpoints require authentication.
