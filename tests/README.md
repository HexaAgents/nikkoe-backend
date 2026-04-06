# Test Suite — nikkoe-backend

## Overview

The test suite uses **pytest** with mocked dependencies (no real database or network calls). Tests are organized by application layer so failures pinpoint the source immediately.

```
tests/
  conftest.py              Shared fixtures (TestClient, mock users, auth overrides)
  test_health.py           Smoke test — app boots and responds
  test_schemas.py          Pydantic model validation rules
  test_errors.py           Error classes and exception handlers
  test_services.py         Business logic with mocked repositories
  test_routers.py          HTTP endpoint validation via TestClient
  ebay/
    conftest.py            eBay-specific fixtures (sample orders, tokens)
    test_ebay_client.py    eBay API client functions
    test_ebay_routers.py   eBay HTTP endpoints
    test_ebay_schemas.py   eBay data shape validation
    test_ebay_sync.py      eBay sync service logic
```

### Layer separation

| File | Layer | What a failure means |
|------|-------|---------------------|
| `test_schemas.py` | Validation | A Pydantic rule is broken |
| `test_services.py` | Business logic | Service logic is wrong (not DB, not HTTP) |
| `test_routers.py` | HTTP | API contract changed or validation bypassed |
| `test_errors.py` | Error handling | Wrong status code or message for an error case |
| `test_health.py` | Smoke | App can't boot at all |

---

## Test Cases by File

### `test_health.py` (2 tests)

| Test | Verifies |
|------|----------|
| `test_health_returns_ok` | `/api/health` returns 200 with `"status": "ok"` and a timestamp |
| `test_health_timestamp_is_valid_iso` | Timestamp is a parseable ISO date |

### `test_schemas.py` (48 tests)

Tests every Pydantic model in `app/schemas.py` for happy path, boundary values, and rejection.

| Class | Tests | What it guards |
|-------|-------|---------------|
| `TestPaginationParams` | 6 | Defaults (50/0), min/max limits, rejects out-of-range |
| `TestPaginatedResult` | 2 | Valid result, empty result |
| `TestCategoryInput` | 4 | Valid name, max length, rejects empty/too-long |
| `TestCustomerInput` | 3 | Valid name, rejects empty/too-long |
| `TestLocationInput` | 4 | Valid code, max 50 chars, rejects empty/over-50 |
| `TestItemInput` | 7 | Minimal/full creation, rejects missing/empty/too-long item_id and description |
| `TestItemUpdateInput` | 3 | All-none defaults, partial update, rejects empty item_id |
| `TestSupplierInput` | 10 | Minimal/full, rejects empty name/too-long name/invalid email/too-long phone/address |
| `TestReceiptInput` | 4 | All optional, full, rejects too-long reference/note |
| `TestReceiptLineInput` | 5 | Valid line, rejects zero/negative quantity, allows zero price, rejects negative price |
| `TestCreateReceiptRequest` | 3 | Valid request, empty lines, invalid line rejects whole request |
| `TestSaleInput` | 3 | All optional, full, rejects too-long note |
| `TestSaleLineInput` | 4 | Valid line, rejects zero quantity, rejects/allows zero price |
| `TestCreateSaleRequest` | 1 | Valid request with lines |
| `TestSupplierQuoteInput` | 7 | Valid/optional, allows zero cost, rejects negative cost/too-long note/missing IDs |
| `TestCreateUserInput` | 4 | Valid, rejects invalid email/short password, accepts exactly 6 chars |
| `TestLoginInput` | 3 | Valid, rejects invalid email, accepts any-length password |
| `TestSignupInput` | 2 | Valid, rejects short password |
| `TestChangePasswordInput` | 3 | Valid, rejects short new password, current password any length |
| `TestVoidRequest` | 2 | Empty (reason optional), with reason |

### `test_errors.py` (13 tests)

| Class | Tests | What it verifies |
|-------|-------|-----------------|
| `TestAppError` | 3 | Stores status/message, is an Exception, str representation |
| `TestNotFoundError` | 2 | 404 with formatted message, is AppError subclass |
| `TestConflictError` | 1 | 409 with message |
| `TestForbiddenError` | 2 | Default "Forbidden" message, custom message |
| `TestPgErrorMap` | 3 | 23505→409, 23503→409, 23502→400 |
| `TestAppErrorHandler` | 2 | Returns correct status/body, custom status |
| `TestValidationErrorHandler` | 1 | Returns 400 with error details list |
| `TestGeneralErrorHandler` | 5 | PG duplicate→409, FK→409, not-null→400, unknown→500, empty message→500 |

### `test_services.py` (27 tests)

All services tested with mocked repositories — no database calls.

| Class | Tests | Key scenarios |
|-------|-------|--------------|
| `TestItemService` | 11 | List (with defaults), get (found/not-found), create, update, delete, quotes, inventory, receipts, sales delegation |
| `TestSaleService` | 6 | List, get (found/not-found), get lines, create, void |
| `TestReceiptService` | 6 | List, get (found/not-found), get lines, create, void |
| `TestCategoryService` | 3 | List, create, delete |
| `TestLocationService` | 3 | List, create, delete |
| `TestSupplierService` | 3 | List, create, delete |
| `TestCustomerService` | 2 | List, create |
| `TestChannelService` | 1 | List |
| `TestInventoryService` | 2 | List movements, list on-hand |
| `TestSupplierQuoteService` | 2 | Create, delete |

### `test_routers.py` (23 tests)

HTTP-level validation tests via FastAPI TestClient. These verify that Pydantic rules are enforced at the endpoint level (not just in the model).

| Class | Tests | What it verifies |
|-------|-------|-----------------|
| `TestAuthValidation` | 4 | Login rejects missing/invalid email; signup rejects short password/missing fields |
| `TestItemValidation` | 4 | Create rejects empty/missing/too-long part number, too-long description |
| `TestCategoryValidation` | 3 | Create rejects empty/missing/too-long name |
| `TestLocationValidation` | 2 | Create rejects empty/too-long code |
| `TestSupplierValidation` | 2 | Create rejects empty name, invalid email |
| `TestSaleValidation` | 2 | Create rejects zero-quantity line, negative price |
| `TestReceiptValidation` | 1 | Create rejects negative-quantity line |
| `TestVoidRequiresProfile` | 2 | Sale/receipt void returns 403 without user profile |
| `TestSupplierQuoteValidation` | 2 | Create rejects negative cost, empty currency |
| `TestCustomerValidation` | 2 | Create rejects empty/missing name |
| `TestUserValidation` | 2 | Create rejects invalid email, short password |
| `TestPaginationQueryParams` | 5 | Items/sales/receipts reject invalid limit/offset |

---

## `conftest.py` — Shared Fixtures

| Fixture | Purpose |
|---------|---------|
| `client` | Unauthenticated `TestClient` — no auth override |
| `mock_user` | `CurrentUser` with full `UserProfile` |
| `mock_user_no_profile` | `CurrentUser` with `profile=None` |
| `authed_client` | `TestClient` with `get_current_user` overridden to `mock_user` |
| `unauthed_client` | `TestClient` with `get_current_user` overridden to profileless user |

Auth is overridden via `app.dependency_overrides` so tests never contact Supabase.

---

## Running Tests

```bash
pip install -r requirements.txt -r requirements-dev.txt

pytest --tb=short -q                                    # all tests
pytest tests/test_schemas.py -v                         # single file
pytest tests/test_services.py::TestItemService -v       # single class
pytest tests/ebay/ -v                                   # all eBay tests
```
