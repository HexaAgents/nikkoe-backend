# app/middleware/

Request-level dependencies that run before route handlers. This folder contains the authentication dependency that verifies JWT tokens and attaches user identity to every protected request.

## How it works

1. The dependency extracts the Bearer token from the `Authorization` header, raising HTTP 401 if absent.
2. It calls `supabase.auth.get_user(token)` to verify the token server-side against Supabase Auth.
3. After verification, it queries the `users` table by `auth_id` to load the application profile (user_id, name, email_address, role).
4. It returns a `CurrentUser` dataclass with the auth ID, email, and profile for use by route handlers.

## Why this design

Verifying via Supabase server-side keeps auth logic centralized and avoids distributing JWT signing keys or reimplementing token verification locally.

## Files

- **auth.py** -- Defines the `get_current_user` FastAPI dependency used on every protected endpoint via `Depends(get_current_user)`. Extracts the Bearer token from the Authorization header, verifies it by calling `supabase.auth.get_user(token)` against Supabase Auth, then queries the `users` table to load the application profile (user_id, name, email_address, role). Returns a `CurrentUser` dataclass with the auth ID, email, and profile, raising HTTP 401 if the token is missing, invalid, or expired.
