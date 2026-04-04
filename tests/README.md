# Test Suite — nikkoe-backend

This document explains the structure, purpose, and reasoning behind every test file in the backend test suite.

---

## Overview

The backend test suite uses **pytest** and is organized into five files, each testing a different layer of the application:

```
tests/
  conftest.py          Shared fixtures used across all test files
  test_health.py       Smoke test — can the app start and respond?
  test_schemas.py      Pydantic model validation — are the rules correct?
  test_errors.py       Error classes and exception handlers
  test_services.py     Business logic with mocked repositories
  test_routers.py      HTTP endpoints via FastAPI's TestClient
```

### Why this structure?

Each file targets a specific layer of the architecture. This means:

- A failure in `test_schemas.py` tells you a validation rule is broken, not a database issue.
- A failure in `test_services.py` tells you business logic is wrong, not an HTTP parsing issue.
- A failure in `test_routers.py` tells you the API contract changed, not an internal logic issue.

When something breaks, you can immediately tell **what layer** caused the problem.

---

## `conftest.py` — Shared Test Configuration

```python
# Sets dummy environment variables before any app code imports
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
```

### Why this file exists

The application uses `pydantic-settings` to read `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and `SUPABASE_ANON_KEY` from the environment at import time (`app/config.py`). Without these variables set, importing any module from `app/` raises a `ValidationError` and every test crashes.

`conftest.py` sets safe dummy values **before** any test file imports app code. pytest loads `conftest.py` before discovering test modules, so this runs first automatically.

### Fixtures provided

| Fixture | What it provides | Why it exists |
|---------|-----------------|---------------|
| `client` | A `TestClient` for the FastAPI app | Makes HTTP requests to the app without a real server |
| `mock_user` | A `CurrentUser` with a full `UserProfile` | Simulates an authenticated user for protected endpoints |
| `mock_user_no_profile` | A `CurrentUser` with `profile=None` | Tests error paths that require a user profile (void operations) |
| `authed_client` | A `TestClient` with auth overridden to `mock_user` | Every protected endpoint can be tested without real Supabase auth |
| `unauthed_client` | A `TestClient` with auth overridden to a profileless user | Tests the "user has no profile" forbidden path |

### Why we override `get_current_user`

Every router endpoint (except `/api/health`, `/api/auth/login`, and `/api/auth/signup`) depends on `get_current_user`, which talks to Supabase to validate a JWT token. In tests, we don't have a real Supabase instance, so we use FastAPI's `dependency_overrides` to replace `get_current_user` with a function that returns a pre-built `CurrentUser` object. This lets us test all endpoint logic without any authentication infrastructure.

---

## `test_health.py` — Smoke Test

```python
def test_health_returns_ok(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
```

### What it tests

- The FastAPI application can start without crashing.
- The `/api/health` endpoint returns a `200` status with `"status": "ok"`.
- The response includes a valid ISO-format timestamp.

### Why it matters

This is the simplest possible test: "Does the app boot and respond?" If this test fails, everything else will too. It's the canary in the coal mine. In CI, this catches catastrophic issues like broken imports, missing environment config, or syntax errors in `main.py`.

---

## `test_schemas.py` — Pydantic Validation Tests

This is the largest test file, covering all 19 Pydantic models defined in `app/schemas.py`.

### What it tests

For every schema, the tests verify:

1. **Happy path** — valid input is accepted and fields are correctly assigned.
2. **Boundary values** — inputs at the exact min/max length or value (e.g., 255 characters for a name, quantity of exactly 1).
3. **Rejection** — invalid input raises `ValidationError` (empty strings, values exceeding limits, negative numbers, invalid emails, missing required fields).

### Why test schemas?

Pydantic schemas are the **first line of defence** against bad data. They run before any service or database code. If a schema allows a negative `quantity` or a 10,000-character `note`, that invalid data flows all the way to the database. Schema tests guarantee that validation rules work exactly as intended.

### Specific schemas and what they guard

| Schema | Guards against |
|--------|---------------|
| `PaginationParams` | Clients requesting 10,000 rows (DoS) or negative offsets |
| `CategoryInput` | Empty or excessively long category names |
| `ItemInput` | Missing part numbers, oversized descriptions |
| `ItemUpdateInput` | Partial updates with invalid field values |
| `SupplierInput` | Invalid email addresses, missing supplier names |
| `ReceiptLineInput` | Zero/negative quantities, negative costs |
| `SaleLineInput` | Zero/negative quantities, negative prices |
| `CreateReceiptRequest` | Invalid nested line items in a receipt |
| `CreateSaleRequest` | Invalid nested line items in a sale |
| `SupplierQuoteInput` | Negative costs, oversized currencies |
| `CreateUserInput` | Invalid emails, passwords shorter than 6 characters |
| `LoginInput` | Missing or invalid email |
| `SignupInput` | Weak passwords |
| `ChangePasswordInput` | New password too short |
| `VoidRequest` | (Permissive — reason is optional) |

### Example: why test "rejects zero quantity"?

A sale line with `quantity: 0` would mean "we sold zero items at a certain price" — a nonsensical record that pollutes financial reports. The Pydantic schema enforces `gt=0` (greater than zero), and the test verifies this rule actually works. Without the test, a future refactor could accidentally change `gt=0` to `ge=0` and nobody would notice until the database fills with zero-quantity records.

---

## `test_errors.py` — Error Classes and Handlers

### What it tests

**Error classes:**
- `AppError` stores `status_code` and `message` correctly.
- `NotFoundError` produces a `404` with a message like `"Item abc-123 not found"`.
- `ConflictError` produces a `409`.
- `ForbiddenError` produces a `403` with a default `"Forbidden"` message.

**Exception handlers** (the functions registered in `main.py`):
- `app_error_handler` converts an `AppError` into a JSON response with the correct status code.
- `validation_error_handler` converts a Pydantic `ValidationError` into a `400` response with human-readable error details.
- `general_error_handler` maps PostgreSQL error codes (duplicate key, foreign key violation, not-null violation) to appropriate HTTP status codes, and falls back to `500` for unknown errors.

**The `PG_ERROR_MAP`:**
- Verifies the mapping dictionary is correct: `23505` (duplicate) maps to `409`, `23503` (FK violation) maps to `409`, `23502` (not-null) maps to `400`.

### Why test error handlers?

Error handlers determine what users see when something goes wrong. If `general_error_handler` fails to recognize a PostgreSQL duplicate-key error, the user gets a generic `500 Internal Server Error` instead of a helpful `409 Duplicate record`. These tests ensure that every known error path produces the correct HTTP status and message.

---

## `test_services.py` — Business Logic Tests

### Architecture: why mock repositories?

The backend follows a three-layer architecture:

```
Router (HTTP) → Service (business logic) → Repository (database)
```

Service classes accept repository instances via constructor injection:

```python
class ItemService:
    def __init__(self, repo, quote_repo, inventory_repo, receipt_repo, sale_repo):
        ...
```

By passing `MagicMock()` objects as repositories, we test the service logic in complete isolation — no database, no network, no Supabase. This makes tests:

- **Fast**: milliseconds per test (no I/O).
- **Deterministic**: no flaky failures from network timeouts.
- **Focused**: when a test fails, the bug is in the service, not the database.

### What it tests

For every service class (`ItemService`, `SaleService`, `ReceiptService`, `CategoryService`, `LocationService`, `SupplierService`, `CustomerService`, `ChannelService`, `InventoryService`, `SupplierQuoteService`), the tests verify:

1. **Delegation** — methods correctly pass arguments to the repository.
2. **Return values** — the service returns whatever the repository returns.
3. **Not-found logic** — `get_item()` and `get_sale()` raise `NotFoundError` when the repository returns `None`.
4. **Default parameters** — `list_items()` defaults to `limit=50, offset=0`.

### Example: testing the not-found path

```python
def test_get_item_raises_not_found(self, service, repos):
    repos["repo"].find_by_id.return_value = None
    with pytest.raises(NotFoundError):
        service.get_item("nonexistent")
```

This test verifies that `ItemService.get_item()` checks the repository result and raises a `404` error. Without this test, a future developer could accidentally remove the `None` check and return `None` directly — causing a `200 OK` response with an empty body instead of a `404`.

---

## `test_routers.py` — HTTP Endpoint Tests

### What it tests

These tests use FastAPI's `TestClient` to make real HTTP requests to the application (without a running server). They test the **full request/response cycle**: URL routing, query parameter parsing, request body validation, dependency injection, and response serialization.

Categories of tests:

| Category | What it verifies |
|----------|-----------------|
| **Health endpoint** | `/api/health` requires no authentication |
| **Auth validation** | Login/signup reject invalid emails and short passwords (422) |
| **Item validation** | Create/update reject empty, missing, or oversized fields (422) |
| **Category validation** | Create rejects empty or oversized names (422) |
| **Location validation** | Create rejects empty or oversized codes (422) |
| **Supplier validation** | Create rejects empty names and invalid emails (422) |
| **Sale validation** | Create rejects invalid line items (zero quantity, negative price) (422) |
| **Receipt validation** | Create rejects invalid line items (negative quantity) (422) |
| **Void authorization** | Void endpoints return 403 when user has no profile |
| **Pagination params** | All list endpoints reject out-of-range limit/offset (422) |
| **Quote validation** | Create rejects negative costs and empty currencies (422) |
| **User validation** | Create rejects invalid emails and short passwords (422) |
| **Customer validation** | Create rejects empty or missing names (422) |

### Why 422 tests?

FastAPI returns `422 Unprocessable Entity` when Pydantic validation fails on request data. These tests verify that the validation rules defined in `app/schemas.py` are actually enforced at the API level. A schema test proves the Pydantic model itself rejects bad data; a router test proves the **endpoint** rejects bad data. The distinction matters because a developer could accidentally bypass validation (e.g., by not using the schema as the endpoint's parameter type).

### Why test void authorization?

The `void_sale` and `void_receipt` endpoints have a manual check:

```python
if not user.profile or not user.profile.user_id:
    raise ForbiddenError("User profile is required to void a sale")
```

This is business logic embedded in the router — it's not covered by schema validation. The test uses `unauthed_client` (which provides a user with no profile) to verify this guard works correctly.

---

## Running the Tests

```bash
# Install dev dependencies (includes pytest, httpx, etc.)
pip install -r requirements.txt -r requirements-dev.txt

# Run all tests
pytest --tb=short -q

# Run a specific file
pytest tests/test_schemas.py -v

# Run a specific test class
pytest tests/test_services.py::TestItemService -v

# Run a single test
pytest tests/test_schemas.py::TestItemInput::test_rejects_empty_part_number -v
```

---

## How to Add New Tests

### Testing a new schema
1. Add a new test class in `test_schemas.py` named `Test<SchemaName>`.
2. Test: valid input, boundary values, every rejection rule.

### Testing a new service
1. Add a new test class in `test_services.py`.
2. Create a `MagicMock()` for each repository the service needs.
3. Test: delegation, return values, error paths.

### Testing a new endpoint
1. Add a new test class in `test_routers.py`.
2. Use `authed_client` for protected endpoints.
3. Test: validation rejection (422), authorization (403), successful response shape.

### Testing a new error type
1. Add a test class in `test_errors.py`.
2. Verify `status_code`, `message`, and that it's an `AppError` subclass.
