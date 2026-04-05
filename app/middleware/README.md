# app/middleware/

Request-level dependencies that run before route handlers. This folder contains the authentication dependency that verifies JWT tokens and attaches user identity to every protected request.

## How it works

1. The dependency extracts the Bearer token from the `Authorization` header, raising HTTP 401 if absent.
2. It calls `supabase.auth.get_user(token)` to verify the token server-side against Supabase Auth.
3. After verification, it queries the `User` table by `auth_id` to load the application profile (id, first_name, last_name, email).
4. It returns a `CurrentUser` dataclass with the auth ID, email, and profile for use by route handlers.

## Files

- **auth.py** -- Defines `get_current_user` FastAPI dependency. Verifies Bearer token via Supabase Auth, then queries the `User` table (PascalCase, integer PK) to load `UserProfile(user_id, first_name, last_name, email)`. Returns `CurrentUser(id, email, profile)`. The User table query is wrapped in try/catch to handle cases where the table is unreachable.
