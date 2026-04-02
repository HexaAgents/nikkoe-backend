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
