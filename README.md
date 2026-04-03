# nikkoe-backend

Express.js API for the Nikkoe inventory management platform.

## Setup

```bash
cp .env.example .env
# Fill in SUPABASE_SERVICE_ROLE_KEY (from Supabase dashboard > Settings > API)
npm install
npm run dev
```

The server starts on `http://localhost:3000`. All routes are under `/api/`.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key (server-side only, never expose) |
| `SUPABASE_ANON_KEY` | Anon/publishable key |
| `PORT` | Server port (default: 3000) |
| `CORS_ORIGIN` | Allowed frontend origin (default: http://localhost:8080) |

## Authentication

All `/api/*` routes (except `/api/health`) require a `Bearer` token in the `Authorization` header. The token is a Supabase Auth JWT obtained by the frontend via `supabase.auth.getSession()`.

## API Endpoints

- `GET /api/health` -- Health check
- `GET/POST /api/receipts`, `GET /api/receipts/:id`, `GET /api/receipts/:id/lines`, `POST /api/receipts/:id/void`
- `GET/POST /api/sales`, `GET /api/sales/:id`, `GET /api/sales/:id/lines`, `POST /api/sales/:id/void`
- `GET/POST/PUT/DELETE /api/items`, `GET /api/items/:id/quotes`, `GET /api/items/:id/inventory`, `GET /api/items/:id/receipts`, `GET /api/items/:id/sales`
- `GET/POST/DELETE /api/suppliers`
- `GET/POST/DELETE /api/locations`
- `GET/POST/DELETE /api/categories`
- `GET /api/channels`
- `GET/POST /api/customers`
- `GET /api/inventory/movements`, `GET /api/inventory/on-hand`
- `GET /api/users/me`, `POST /api/users`
- `POST/DELETE /api/supplier-quotes`

All list endpoints support `?limit=` and `?offset=` query parameters and return `{ data: [...], total: N }`.

## Project Structure

```
src/
  server.ts              App entry point -- creates Express, mounts routes, starts listening
  container.ts           Composition root -- wires all repositories, services, and routers

  infrastructure/
    supabase.ts          Supabase client singleton (service role key)

  middleware/
    asyncHandler.ts      Wraps async route handlers to auto-catch errors
    auth.ts              JWT auth middleware -- verifies token, attaches user to request
    errorHandler.ts      Global error handler -- maps Zod/AppError/Postgres errors to HTTP responses

  errors/
    index.ts             AppError base class plus NotFoundError (404), ConflictError (409), ForbiddenError (403)

  types/
    domain.types.ts      All domain entity interfaces (Category, Item, Receipt, Sale, Supplier, etc.)
    db.types.ts          DbClient type alias for the Supabase client
    express.d.ts         Extends Express Request with a user property
    pagination.types.ts  PaginationParams and PaginatedResult interfaces

  schemas/
    index.ts             All Zod validation schemas (one per entity plus shared primitives)

  repositories/
    interfaces.ts        All repository interfaces defining data-access contracts
    utils/
      batchLoad.ts       Generic helper for batch-fetching rows by ID into a Map
    *.repository.ts      Supabase implementations (one per domain entity)

  services/
    interfaces.ts        All service interfaces defining business-logic contracts
    *.service.ts          Business logic (one per domain) -- validates input, enforces rules, delegates to repos

  routes/
    *.ts                 Express routers (one per domain) -- parse HTTP, call services, return responses

supabase/
  migrations/            SQL migrations (e.g. atomic receipt/sale creation RPCs)
```
