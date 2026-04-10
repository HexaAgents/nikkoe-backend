# app/middleware/

Request-level dependencies that run before route handlers. This folder contains the authentication dependency that verifies JWT tokens and attaches user identity to every protected request.

## How it works

1. The dependency extracts the Bearer token from the `Authorization` header, raising HTTP 401 if absent.
2. It checks a 60-second TTL in-memory cache keyed by the token. If cached, returns the `CurrentUser` immediately (avoids redundant Supabase calls during request bursts).
3. On cache miss, it calls `supabase.auth.get_user(token)` to verify the token server-side against Supabase Auth.
4. After verification, it queries the `User` table by `auth_id` to load the application profile (id, first_name, last_name, email).
5. It caches and returns a `CurrentUser` dataclass with the auth ID, email, and profile for use by route handlers.

## Files

- **auth.py** -- Defines `get_current_user` FastAPI dependency with a `cachetools.TTLCache` (128 entries, 60s TTL) to avoid re-validating the same token on concurrent requests. Verifies Bearer token via Supabase Auth, then queries the `User` table to load `UserProfile(user_id, first_name, last_name, email)`. Returns `CurrentUser(id, email, profile)`.
