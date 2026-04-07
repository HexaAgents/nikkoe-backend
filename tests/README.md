# Test Suite — nikkoe-backend

## Overview

**434 tests** across 12 files, using **pytest** with mocked dependencies (no real database or network calls). Tests are organized by purpose so failures pinpoint the problem immediately.

```
tests/
  conftest.py                   Shared fixtures (TestClient, mock users, auth overrides)
  test_health.py            (2) Smoke test — app boots and responds
  test_schemas.py          (83) Pydantic model validation rules
  test_errors.py           (19) Error classes and exception handlers
  test_services.py         (53) Business logic with mocked repositories
  test_routers.py          (47) HTTP input validation (reject bad data)
  test_router_responses.py (94) HTTP happy-path tests (every endpoint)
  test_auth_enforcement.py (45) Auth gate — 401 on every protected route
  test_response_contracts.py(30) Frontend contract — JSON shape assertions
  ebay/
    conftest.py                 eBay-specific fixtures
    test_ebay_client.py    (18) eBay API client functions
    test_ebay_routers.py   (16) eBay HTTP endpoints
    test_ebay_schemas.py    (8) eBay data shape validation
    test_ebay_sync.py      (19) eBay sync service logic
```

### Layer separation

| File | Layer | What a failure means |
|------|-------|---------------------|
| `test_schemas.py` | Validation | A Pydantic rule is broken |
| `test_services.py` | Business logic | Service logic is wrong (not DB, not HTTP) |
| `test_routers.py` | HTTP validation | Bad data is no longer rejected |
| `test_router_responses.py` | HTTP behaviour | An endpoint's status code, delegation, or data flow changed |
| `test_auth_enforcement.py` | Security | A protected endpoint lost its auth guard |
| `test_response_contracts.py` | API contract | The JSON shape the frontend depends on changed |
| `test_errors.py` | Error handling | Wrong status code or message for an error case |
| `test_health.py` | Smoke | App can't boot at all |

---

## Test Cases by File

### `test_health.py` (2 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_health_returns_ok` | `GET /api/health` returns 200 with `"status": "ok"` and a `timestamp` key | The app is not booting or the health endpoint was removed/broken |
| `test_health_timestamp_is_valid_iso` | The `timestamp` value in the health response parses as a valid ISO 8601 date | The health endpoint is returning a malformed or missing timestamp |

---

### `test_schemas.py` (83 tests)

Tests every Pydantic model in `app/schemas.py` for happy path, boundary values, and rejection.

#### TestPaginationParams (6 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_defaults` | Default values are `limit=50, offset=0` | The default pagination changed, which will break every list endpoint's default behaviour |
| `test_custom_values` | Accepts valid custom `limit` and `offset` | Valid pagination values are being rejected |
| `test_limit_minimum` | Accepts `limit=1` (minimum allowed) | The minimum limit boundary changed |
| `test_limit_maximum` | Accepts `limit=100` (maximum allowed) | The maximum limit boundary changed |
| `test_limit_out_of_range` | Rejects `limit` values of -1, 0, 101, 999 | Out-of-range limits are no longer rejected — users can request absurd page sizes |
| `test_negative_offset_rejected` | Rejects `offset=-1` | Negative offsets are allowed, which could cause DB errors or return wrong data |

#### TestPaginatedResult (2 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_valid` | Accepts a result with `data` list and `total` int | The paginated response model is broken |
| `test_empty` | Accepts an empty `data: [], total: 0` | Empty list responses are being rejected |

#### TestCategoryInput (4 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_valid` | Accepts a valid category name | Basic category creation is broken |
| `test_max_length` | Accepts name at exactly 255 characters | Max-length names are wrongly rejected |
| `test_rejects_empty` | Rejects empty string name | Users can create categories with blank names |
| `test_rejects_too_long` | Rejects name over 255 characters | Oversized names are accepted, risking DB errors |

#### TestCustomerInput (3 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_valid` | Accepts a valid customer name | Basic customer creation is broken |
| `test_rejects_empty` | Rejects empty string name | Users can create customers with blank names |
| `test_rejects_too_long` | Rejects name over 255 characters | Oversized names are accepted |

#### TestLocationInput (4 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_valid` | Accepts a valid location code | Basic location creation is broken |
| `test_max_length_50` | Accepts code at exactly 50 characters | Max-length codes are wrongly rejected |
| `test_rejects_empty` | Rejects empty string code | Users can create locations with blank codes |
| `test_rejects_over_50` | Rejects code over 50 characters | Oversized codes are accepted |

#### TestItemInput (7 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_minimal` | Accepts item with only `item_id` (part number) | Basic item creation is broken |
| `test_fully_populated` | Accepts item with all optional fields filled | Optional fields are being rejected |
| `test_description_at_max` | Accepts description at exactly 1000 characters | Max-length descriptions are wrongly rejected |
| `test_rejects_missing_item_id` | Rejects item with no `item_id` | Items can be created without a part number |
| `test_rejects_empty_item_id` | Rejects item with empty `item_id` | Items can be created with a blank part number |
| `test_rejects_item_id_too_long` | Rejects `item_id` over 255 characters | Oversized part numbers are accepted |
| `test_rejects_description_too_long` | Rejects description over 1000 characters | Oversized descriptions are accepted |

#### TestItemUpdateInput (3 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_all_none_by_default` | All fields default to `None` (partial update) | Partial updates require all fields, breaking PATCH semantics |
| `test_partial_update` | Accepts only a `description` without `item_id` | Partial updates are broken |
| `test_rejects_empty_item_id` | Rejects update with empty `item_id` | Part number can be blanked out via update |

#### TestSupplierInput (10 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_minimal` | Accepts supplier with only `name` | Basic supplier creation is broken |
| `test_fully_populated` | Accepts supplier with name, email, phone, address | Optional fields are being rejected |
| `test_rejects_empty_name` | Rejects empty supplier name | Suppliers can be created with blank names |
| `test_rejects_missing_name` | Rejects request missing `name` field | Suppliers can be created without a name |
| `test_rejects_name_too_long` | Rejects name over 255 characters | Oversized names are accepted |
| `test_rejects_invalid_email` | Rejects malformed email address | Invalid emails are stored in the database |
| `test_rejects_phone_too_long` | Rejects phone over 20 characters | Oversized phone numbers are accepted |
| `test_phone_at_max` | Accepts phone at exactly 20 characters | Max-length phones are wrongly rejected |
| `test_rejects_address_too_long` | Rejects address over 500 characters | Oversized addresses are accepted |
| `test_address_at_max` | Accepts address at exactly 500 characters | Max-length addresses are wrongly rejected |

#### TestReceiptInput (4 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_all_optional` | Accepts receipt with no fields (all optional) | Receipt creation requires fields that should be optional |
| `test_fully_populated` | Accepts receipt with supplier_id, reference, note | Optional fields are being rejected |
| `test_rejects_reference_too_long` | Rejects reference over 255 characters | Oversized references are accepted |
| `test_rejects_note_too_long` | Rejects note over 1000 characters | Oversized notes are accepted |

#### TestReceiptLineInput (5 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_valid` | Accepts a valid receipt line with quantity, price, currency | Basic receipt line creation is broken |
| `test_rejects_zero_quantity` | Rejects `quantity=0` | Zero-quantity lines are accepted, creating empty receipts |
| `test_rejects_negative_quantity` | Rejects `quantity=-1` | Negative quantities are accepted, corrupting stock |
| `test_allows_zero_unit_price` | Accepts `unit_price=0` (free items) | Free items can't be received |
| `test_rejects_negative_unit_price` | Rejects `unit_price=-1` | Negative prices are accepted, corrupting financials |

#### TestCreateReceiptRequest (3 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_valid` | Accepts a valid receipt with lines | Receipt creation is fundamentally broken |
| `test_empty_lines` | Accepts receipt with empty lines list | Depends on business rule — empty receipts may or may not be valid |
| `test_invalid_line_rejects_whole_request` | One bad line rejects the entire receipt | Invalid lines can slip through in a batch |

#### TestSaleInput (3 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_all_optional` | Accepts sale with no fields (all optional) | Sale creation requires fields that should be optional |
| `test_fully_populated` | Accepts sale with customer_id, channel_id, note | Optional fields are being rejected |
| `test_rejects_note_too_long` | Rejects note over 1000 characters | Oversized notes are accepted |

#### TestSaleLineInput (4 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_valid` | Accepts a valid sale line | Basic sale line creation is broken |
| `test_rejects_zero_quantity` | Rejects `quantity=0` | Zero-quantity lines are accepted, creating empty sales |
| `test_allows_zero_unit_price` | Accepts `unit_price=0` (free items) | Free items can't be sold |
| `test_rejects_negative_unit_price` | Rejects `unit_price=-1` | Negative prices are accepted, corrupting revenue |

#### TestCreateSaleRequest (1 test)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_valid_with_lines` | Accepts a valid sale with line items | Sale creation is fundamentally broken |

#### TestSupplierQuoteInput (7 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_valid` | Accepts a valid quote with item_id, supplier_id, cost, currency_id | Basic quote creation is broken |
| `test_with_optional_fields` | Accepts quote with date_time and note | Optional fields are being rejected |
| `test_allows_zero_cost` | Accepts `cost=0` | Zero-cost quotes (free supply) can't be recorded |
| `test_rejects_negative_cost` | Rejects `cost=-1` | Negative costs are accepted |
| `test_rejects_note_too_long` | Rejects note over 500 characters | Oversized notes are accepted |
| `test_rejects_missing_item_id` | Rejects quote without `item_id` | Quotes can be created for no item |
| `test_rejects_missing_supplier_id` | Rejects quote without `supplier_id` | Quotes can be created for no supplier |

#### TestCreateUserInput (4 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_valid` | Accepts valid email and 6+ char password | User creation is broken |
| `test_rejects_invalid_email` | Rejects malformed email | Users can sign up with invalid emails |
| `test_rejects_short_password` | Rejects password under 6 characters | Weak passwords are accepted |
| `test_accepts_exactly_6_char_password` | Accepts exactly 6 character password (boundary) | The minimum password length boundary is wrong |

#### TestLoginInput (3 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_valid` | Accepts valid email and password | Login is broken at the validation level |
| `test_rejects_invalid_email` | Rejects malformed email | Login accepts garbage emails |
| `test_accepts_any_length_password` | Accepts any-length password (no min on login) | Login rejects short passwords — users with old passwords can't log in |

#### TestSignupInput (2 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_valid` | Accepts valid email and 6+ char password | Signup is broken |
| `test_rejects_short_password` | Rejects password under 6 characters | Weak passwords are accepted at signup |

#### TestChangePasswordInput (3 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_valid` | Accepts valid current and new passwords | Change-password is broken |
| `test_rejects_short_new_password` | Rejects new password under 6 characters | Users can set weak passwords |
| `test_current_password_any_length` | Accepts any-length current password | Users with old passwords can't change them |

#### TestVoidRequest (2 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_empty` | Accepts void request with no reason (optional) | Void requires a reason when it shouldn't |
| `test_with_reason` | Accepts void request with a reason string | Providing a reason is rejected |

#### TestTransferInput (7 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_valid` | Accepts valid transfer with from_stock_id, to_location_id, quantity | Stock transfers are broken |
| `test_rejects_missing_quantity` | Rejects transfer missing quantity | Transfers can be created with undefined quantity |
| `test_rejects_zero_quantity` | Rejects `quantity=0` | Zero-quantity transfers are accepted |
| `test_rejects_negative_quantity` | Rejects `quantity=-1` | Negative transfers are accepted, corrupting stock |
| `test_notes_optional` | Accepts transfer with no notes | Notes are wrongly required |
| `test_notes_at_max` | Accepts notes at 500 characters | Max-length notes are wrongly rejected |
| `test_rejects_notes_too_long` | Rejects notes over 500 characters | Oversized notes are accepted |

---

### `test_errors.py` (19 tests)

#### TestAppError (3 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_stores_status_and_message` | `AppError(400, "bad")` stores `.status_code=400` and `.message="bad"` | Error objects don't carry the right status/message — all error responses will be wrong |
| `test_is_exception` | `AppError` is a subclass of `Exception` | Errors can't be raised/caught properly |
| `test_str_representation` | `str(AppError(400, "bad"))` returns a readable string | Error logging will be broken |

#### TestNotFoundError (2 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_404_with_formatted_message` | `NotFoundError("Item", "42")` has status 404 and message containing "Item" and "42" | Not-found responses return the wrong status code or a generic message |
| `test_is_app_error` | `NotFoundError` is a subclass of `AppError` | Not-found errors won't be caught by the AppError handler |

#### TestConflictError (1 test)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_409` | `ConflictError("dup")` has status 409 | Duplicate-key errors return the wrong status code |

#### TestForbiddenError (2 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_default_message` | `ForbiddenError()` uses default message "Forbidden" | Forbidden responses have no message |
| `test_custom_message` | `ForbiddenError("No access")` uses the custom message | Custom forbidden messages are ignored |

#### TestPgErrorMap (3 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_duplicate_key` | Postgres error 23505 maps to HTTP 409 | Duplicate-key DB errors return 500 instead of 409 |
| `test_foreign_key_violation` | Postgres error 23503 maps to HTTP 409 | FK violation DB errors return 500 instead of 409 |
| `test_not_null_violation` | Postgres error 23502 maps to HTTP 400 | Not-null DB errors return 500 instead of 400 |

#### TestAppErrorHandler (2 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_returns_correct_status_and_body` | Handler returns the error's status code and `{error: message}` body | All application errors return wrong HTTP status or body format |
| `test_custom_status` | Handler respects non-default status codes | Custom error codes (e.g. 403, 409) are ignored |

#### TestValidationErrorHandler (1 test)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_returns_400_with_details` | Pydantic validation errors return 400 with an error details list | Validation errors return 500 or a useless message — the frontend can't show field-level errors |

#### TestGeneralErrorHandler (5 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_pg_duplicate_key_error` | PG duplicate key → HTTP 409 | Duplicate records cause 500 instead of a user-friendly conflict error |
| `test_pg_foreign_key_error` | PG FK violation → HTTP 409 | Deleting a referenced record causes 500 |
| `test_pg_not_null_error` | PG not-null violation → HTTP 400 | Missing required DB columns cause 500 |
| `test_unknown_error_returns_500` | Unrecognized exceptions → HTTP 500 with "Internal server error" | Unknown errors leak stack traces or return wrong status |
| `test_empty_exception_message` | Exception with empty message → HTTP 500 with fallback text | Empty exceptions cause empty or broken responses |

---

### `test_services.py` (53 tests)

All services tested with mocked repositories — no database calls.

#### TestItemService (11 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_list_items_delegates_to_repo` | `list_items(10, 0)` calls `repo.find_all(10, 0)` | Item listing is not reaching the database |
| `test_list_items_uses_defaults` | `list_items()` uses default `limit=50, offset=0` | Default pagination changed — frontend will get different page sizes |
| `test_get_item_returns_item_when_found` | Returns the item dict when repo finds it | Found items are not returned properly |
| `test_get_item_raises_not_found` | Raises `NotFoundError` (404) when repo returns None | Missing items return 200 with null instead of 404 |
| `test_create_item_delegates_to_repo` | Passes data dict to `repo.create` and returns result | Item creation is broken |
| `test_update_item_delegates_to_repo` | Passes id and data to `repo.update` | Item updates are broken |
| `test_delete_item_delegates_to_repo` | Calls `repo.remove` with the correct id | Item deletion is broken |
| `test_get_item_quotes_delegates` | Calls `quote_repo.find_by_item_id` | Supplier quotes for an item are not fetched |
| `test_get_item_inventory_delegates` | Calls `inventory_repo.find_by_item_id` | Inventory for an item is not fetched |
| `test_get_item_receipts_delegates` | Calls `receipt_repo.find_by_item_id` | Receipt history for an item is not fetched |
| `test_get_item_sales_delegates` | Calls `sale_repo.find_by_item_id` | Sale history for an item is not fetched |

#### TestSaleService (6 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_list_sales` | `list_sales(25, 10)` calls `repo.find_all(25, 10)` | Sale listing is broken |
| `test_get_sale_returns_sale` | Returns sale dict when found | Found sales are not returned |
| `test_get_sale_raises_not_found` | Raises 404 when sale is missing | Missing sales don't return 404 |
| `test_get_sale_lines` | Calls `repo.find_lines` with sale_id | Sale line items are not fetched |
| `test_create_sale` | Passes sale data and lines to `repo.create` | Sale creation is broken |
| `test_void_sale` | Passes sale_id, user_id, reason to `repo.void_sale` | Sale voiding is broken |

#### TestReceiptService (6 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_list_receipts` | `list_receipts(50, 0)` calls `repo.find_all(50, 0)` | Receipt listing is broken |
| `test_get_receipt_returns_receipt` | Returns receipt dict when found | Found receipts are not returned |
| `test_get_receipt_raises_not_found` | Raises 404 when receipt is missing | Missing receipts don't return 404 |
| `test_get_receipt_lines` | Calls `repo.find_lines` with receipt_id | Receipt line items are not fetched |
| `test_create_receipt` | Passes receipt data and lines to `repo.create` | Receipt creation is broken |
| `test_void_receipt` | Passes receipt_id, user_id, reason to `repo.void_receipt` | Receipt voiding is broken |

#### TestCategoryService (3 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_list_categories` | Delegates to `repo.find_all` | Category listing is broken |
| `test_create_category` | Passes `{name}` to `repo.create` | Category creation is broken |
| `test_delete_category` | Calls `repo.remove` with id | Category deletion is broken |

#### TestLocationService (3 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_list_locations` | Delegates to `repo.find_all` | Location listing is broken |
| `test_create_location` | Passes data to `repo.create` | Location creation is broken |
| `test_delete_location` | Calls `repo.remove` with id | Location deletion is broken |

#### TestSupplierService (3 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_list_suppliers` | Delegates to `repo.find_all` | Supplier listing is broken |
| `test_create_supplier` | Passes data to `repo.create` | Supplier creation is broken |
| `test_delete_supplier` | Calls `repo.remove` with id | Supplier deletion is broken |

#### TestCustomerService (2 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_list_customers` | Delegates to `repo.find_all` | Customer listing is broken |
| `test_create_customer` | Passes data to `repo.create` | Customer creation is broken |

#### TestChannelService (1 test)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_list_channels` | Delegates to `repo.find_all` | Channel listing is broken (sales channel dropdown won't load) |

#### TestInventoryService (2 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_list_movements` | Delegates to `repo.find_movements` | Inventory movement log is broken |
| `test_list_on_hand` | Delegates to `repo.find_on_hand` | On-hand inventory view is broken |

#### TestSupplierQuoteService (2 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_create_quote` | Passes data to `repo.create` | Quote creation is broken |
| `test_delete_quote` | Calls `repo.remove` with id | Quote deletion is broken |

#### TestSaleServiceSearch (3 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_list_sales_with_search_delegates_to_search` | When `search` is provided, calls `repo.search_by_part_number` instead of `find_all` | **The "recent sales" search is broken** — search term is ignored and all sales are returned |
| `test_list_sales_without_search_delegates_to_find_all` | When no `search`, calls `repo.find_all` | Normal sale listing is broken when not searching |
| `test_list_sales_none_search_delegates_to_find_all` | When `search=None`, calls `repo.find_all` | Passing None as search triggers the search path instead of listing |

#### TestReceiptServiceSearch (2 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_list_receipts_with_search_delegates_to_search` | When `search` is provided, calls `repo.search_by_part_number` | Receipt search is broken — search term is ignored |
| `test_list_receipts_without_search_delegates_to_find_all` | When no `search`, calls `repo.find_all` | Normal receipt listing is broken when not searching |

#### TestItemServiceSearch (2 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_search_items_delegates_to_repo` | Calls `repo.search` with query, limit, offset, `in_stock=False` | Item search is broken |
| `test_search_items_with_in_stock` | Forwards `in_stock=True` to `repo.search` | The "in stock only" filter is broken |

#### TestInventoryServiceTransfer (2 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_transfer_stock_delegates_to_repo` | Passes from_stock_id, to_location_id, quantity, user_id, notes to `repo.create_transfer` | Stock transfers are broken |
| `test_transfer_stock_without_user_or_notes` | Defaults user_id and notes to None | Transfers fail when user_id or notes aren't provided |

#### TestCurrencyService (2 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_list_currencies` | Calls `repo.find_all(50, 0)` and returns result | Currency listing is broken — currency dropdown won't load |
| `test_list_currencies_uses_defaults` | `list_currencies()` defaults to `limit=50, offset=0` | Default pagination changed |

#### TestUserService (3 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_get_profile_returns_profile_when_present` | Returns the UserProfile when it exists | User profile endpoint is broken |
| `test_get_profile_raises_not_found_when_none` | Raises 404 when profile is None | Users without profiles don't get a 404 — they get a crash or null |
| `test_create_user_delegates_to_repo` | Passes email and password to `repo.create_auth_user` | User creation is broken |

---

### `test_routers.py` (47 tests)

HTTP-level validation tests via FastAPI TestClient. Verify that Pydantic rules and query-param constraints are enforced at the endpoint level.

#### TestAuthValidation (4 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_login_rejects_missing_email` | `POST /api/auth/login` without email returns 422 | Login accepts requests with no email |
| `test_login_rejects_invalid_email` | `POST /api/auth/login` with `"bad"` as email returns 422 | Login accepts malformed emails |
| `test_signup_rejects_short_password` | `POST /api/auth/signup` with 5-char password returns 422 | Signup accepts weak passwords |
| `test_signup_rejects_missing_fields` | `POST /api/auth/signup` with empty body returns 422 | Signup accepts empty requests |

#### TestItemValidation (4 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_create_item_rejects_empty_part_number` | `POST /api/items/` with `item_id=""` returns 422 | Items can be created with blank part numbers |
| `test_create_item_rejects_missing_part_number` | `POST /api/items/` with no `item_id` returns 422 | Items can be created without a part number |
| `test_create_item_rejects_part_number_too_long` | `POST /api/items/` with 256-char `item_id` returns 422 | Oversized part numbers are accepted |
| `test_create_item_rejects_description_too_long` | `POST /api/items/` with 1001-char description returns 422 | Oversized descriptions are accepted |

#### TestCategoryValidation (3 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_create_category_rejects_empty_name` | `POST /api/categories/` with `name=""` returns 422 | Categories with blank names can be created |
| `test_create_category_rejects_missing_name` | `POST /api/categories/` with no `name` returns 422 | Categories without a name can be created |
| `test_create_category_rejects_name_too_long` | `POST /api/categories/` with 256-char name returns 422 | Oversized names are accepted |

#### TestLocationValidation (2 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_create_rejects_empty_code` | `POST /api/locations/` with empty code returns 422 | Locations with blank codes can be created |
| `test_create_rejects_code_too_long` | `POST /api/locations/` with 51-char code returns 422 | Oversized codes are accepted |

#### TestSupplierValidation (2 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_create_rejects_empty_name` | `POST /api/suppliers/` with empty name returns 422 | Suppliers with blank names can be created |
| `test_create_rejects_invalid_email` | `POST /api/suppliers/` with `"bad-email"` returns 422 | Invalid supplier emails are stored |

#### TestSaleValidation (2 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_create_sale_rejects_invalid_line` | `POST /api/sales/` with `quantity=0` line returns 422 | Zero-quantity sale lines are accepted |
| `test_create_sale_rejects_negative_price` | `POST /api/sales/` with `unit_price=-5` returns 422 | Negative prices are accepted, corrupting revenue |

#### TestReceiptValidation (1 test)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_create_receipt_rejects_invalid_line` | `POST /api/receipts/` with `quantity=-1` returns 422 | Negative receipt quantities are accepted, corrupting stock |

#### TestVoidRequiresProfile (2 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_void_sale_forbidden_without_profile` | `POST /api/sales/1/void` returns 403 when user has no profile | Users without profiles can void sales — no audit trail |
| `test_void_receipt_forbidden_without_profile` | `POST /api/receipts/1/void` returns 403 when user has no profile | Users without profiles can void receipts — no audit trail |

#### TestSupplierQuoteValidation (2 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_create_quote_rejects_negative_cost` | `POST /api/supplier-quotes/` with `cost=-1` returns 422 | Negative costs are accepted |
| `test_create_quote_rejects_empty_currency` | `POST /api/supplier-quotes/` with `currency=""` returns 422 | Quotes with no currency are accepted |

#### TestCustomerValidation (2 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_create_rejects_empty_name` | `POST /api/customers/` with `name=""` returns 422 | Customers with blank names can be created |
| `test_create_rejects_missing_name` | `POST /api/customers/` with no `name` returns 422 | Customers without a name can be created |

#### TestUserValidation (2 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_create_user_rejects_invalid_email` | `POST /api/users/` with invalid email returns 422 | Users can be created with bad emails |
| `test_create_user_rejects_short_password` | `POST /api/users/` with 5-char password returns 422 | Users can be created with weak passwords |

#### TestPaginationQueryParams (11 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_items_rejects_limit_zero` | `GET /api/items/?limit=0` returns 422 | Zero-limit is accepted (empty page) |
| `test_items_rejects_limit_over_max` | `GET /api/items/?limit=100001` returns 422 | Absurdly large page sizes are accepted |
| `test_items_rejects_negative_offset` | `GET /api/items/?offset=-1` returns 422 | Negative offsets are accepted |
| `test_sales_rejects_limit_zero` | `GET /api/sales/?limit=0` returns 422 | Zero-limit is accepted on sales |
| `test_sales_rejects_limit_over_max` | `GET /api/sales/?limit=101` returns 422 | Sales page size exceeds 100 max |
| `test_receipts_rejects_negative_offset` | `GET /api/receipts/?offset=-1` returns 422 | Negative offsets on receipts |
| `test_receipts_rejects_limit_zero` | `GET /api/receipts/?limit=0` returns 422 | Zero-limit on receipts |
| `test_customers_rejects_limit_zero` | `GET /api/customers/?limit=0` returns 422 | Zero-limit on customers |
| `test_channels_rejects_negative_offset` | `GET /api/channels/?offset=-1` returns 422 | Negative offsets on channels |
| `test_currencies_rejects_limit_zero` | `GET /api/currencies/?limit=0` returns 422 | Zero-limit on currencies |
| `test_inventory_movements_rejects_negative_offset` | `GET /api/inventory/movements?offset=-1` returns 422 | Negative offsets on movements |

#### TestReceiptValidationExtra (1 test)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_create_receipt_rejects_zero_quantity` | `POST /api/receipts/` with `quantity=0` returns 422 | Zero-quantity receipt lines are accepted |

#### TestSaleValidationExtra (1 test)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_create_sale_rejects_zero_price_negative` | `POST /api/sales/` with `unit_price=-0.01` returns 422 | Barely-negative prices slip through |

#### TestInventoryTransferValidation (4 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_transfer_rejects_missing_from_stock_id` | `POST /api/inventory/transfer` without `from_stock_id` returns 422 | Transfers can be created with no source |
| `test_transfer_rejects_zero_quantity` | Transfer with `quantity=0` returns 422 | Zero-quantity transfers are accepted |
| `test_transfer_rejects_negative_quantity` | Transfer with `quantity=-1` returns 422 | Negative transfers are accepted, corrupting stock |
| `test_transfer_rejects_notes_too_long` | Transfer with 501-char notes returns 422 | Oversized notes are accepted |

#### TestItemSearchValidation (2 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_search_rejects_missing_query` | `GET /api/items/search` (no `q` param) returns 422 | Search without a query term is accepted |
| `test_search_rejects_query_too_long` | `GET /api/items/search?q=<256 chars>` returns 422 | Absurdly long search queries are accepted |

#### TestChangePasswordValidation (2 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_change_password_rejects_short_new_password` | `POST /api/auth/change-password` with 5-char new password returns 422 | Users can set weak passwords |
| `test_change_password_rejects_missing_current` | `POST /api/auth/change-password` without current_password returns 422 | Password can be changed without verifying the current one |

---

### `test_router_responses.py` (94 tests)

Happy-path and behaviour tests for **every** API endpoint. Services are mocked; tests verify correct status codes, response shapes, argument delegation, and data flow.

#### TestAuthLogin (3 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_login_returns_200_with_user_and_session` | Successful login returns 200 with `user.id`, `user.email`, `session.access_token`, `session.refresh_token`, `session.expires_in`, `session.token_type` | **Login is broken** — users cannot sign in |
| `test_login_returns_401_on_bad_credentials` | Supabase exception → 401 | Bad credentials return 200 or 500 instead of 401 |
| `test_login_returns_401_when_user_is_none` | Supabase returns null user → 401 | Null user responses are not handled |

#### TestAuthSignup (4 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_signup_returns_200_with_user` | Successful signup returns 200 with user and session | **Signup is broken** — new users cannot register |
| `test_signup_returns_null_session_when_confirmation_required` | When email confirmation is needed, session is null but signup still returns 200 | Confirmation-required signups are treated as failures |
| `test_signup_returns_400_on_failure` | Supabase exception → 400 | Signup failures return 500 instead of 400 |
| `test_signup_returns_400_when_user_none` | Supabase returns null user → 400 | Null user on signup is not handled |

#### TestAuthMe (2 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_get_me_with_profile` | Returns `{user: {id, email}, profile: {user_id, name, email_address}}` | **The "who am I" endpoint is broken** — the frontend can't show the user's name |
| `test_get_me_without_profile` | Returns `{user: {id, email}, profile: null}` when profile is missing | Users without profiles cause a crash instead of returning null |

#### TestAuthChangePassword (3 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_change_password_success` | Returns `{success: true}` | **Change password is broken** |
| `test_change_password_wrong_current` | Wrong current password → 400 | Wrong password is not checked — anyone can change passwords |
| `test_change_password_update_failure` | Supabase update failure → 400 | Update failures return 500 instead of 400 |

#### TestSaleEndpoints (11 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_list_sales_returns_200` | `GET /api/sales/` returns 200 with `{data, total}` | **Recent sales list is broken** — the sales page won't load |
| `test_list_sales_passes_default_pagination` | Default pagination is `limit=50, offset=0, search=None` | Default page size changed silently |
| `test_list_sales_passes_custom_pagination` | `?limit=10&offset=5` is forwarded to service | Custom pagination is ignored |
| `test_list_sales_with_search` | `?search=PART-1` is forwarded to service | **Sale search is broken** — search bar does nothing |
| `test_get_sale_returns_200` | `GET /api/sales/1` returns 200 with sale data | Sale detail page is broken |
| `test_get_sale_not_found` | Non-existent sale → 404 | Missing sales return 200 or 500 |
| `test_get_sale_lines_returns_200` | `GET /api/sales/1/lines` returns line items | Sale line items don't load |
| `test_create_sale_returns_201` | `POST /api/sales/` returns 201 with sale object | **Sale creation is broken** |
| `test_create_sale_injects_user_id` | The authenticated user's `user_id` is injected into sale data | Sales have no user_id — no audit trail |
| `test_void_sale_returns_success` | `POST /api/sales/1/void` returns `{success: true}` with reason and user_id | **Sale voiding is broken** |
| `test_void_sale_without_reason` | Void with no reason passes `None` for reason | Void without reason crashes |

#### TestReceiptEndpoints (11 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_list_receipts_returns_200` | `GET /api/receipts/` returns 200 with `{data, total}` | **Receipt list is broken** |
| `test_list_receipts_passes_default_pagination` | Default pagination is `limit=50, offset=0, search=None` | Default page size changed |
| `test_list_receipts_passes_custom_pagination` | Custom limit/offset is forwarded | Custom pagination is ignored |
| `test_list_receipts_with_search` | Search term is forwarded to service | **Receipt search is broken** |
| `test_get_receipt_returns_200` | `GET /api/receipts/1` returns 200 | Receipt detail page is broken |
| `test_get_receipt_not_found` | Non-existent receipt → 404 | Missing receipts return 200 or 500 |
| `test_get_receipt_lines_returns_200` | Lines endpoint returns array | Receipt line items don't load |
| `test_create_receipt_returns_201` | `POST /api/receipts/` returns 201 | **Receipt creation is broken** |
| `test_create_receipt_injects_user_id` | User's `user_id` is injected into receipt data | Receipts have no user_id — no audit trail |
| `test_void_receipt_returns_success` | Void returns `{success: true}` | **Receipt voiding is broken** |
| `test_void_receipt_without_reason` | Void with no reason works | Void without reason crashes |

#### TestItemEndpoints (18 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_list_items_returns_200` | `GET /api/items/` returns 200 with `{data, total}` | **Item list is broken** |
| `test_list_items_passes_default_pagination` | Default is `limit=1000, offset=0` | Default page size changed |
| `test_list_items_passes_custom_pagination` | Custom limit/offset forwarded | Custom pagination ignored |
| `test_search_items_returns_200` | `GET /api/items/search?q=PART` returns 200 | **Item search is broken** |
| `test_search_items_passes_query_and_defaults` | Query, limit=1000, offset=0, in_stock=False forwarded | Search parameters are wrong |
| `test_search_items_with_in_stock` | `in_stock=true` is forwarded as `True` | In-stock filter is broken |
| `test_search_items_custom_pagination` | Custom limit/offset on search | Search pagination broken |
| `test_get_item_returns_200` | `GET /api/items/1` returns 200 with item data | Item detail page is broken |
| `test_get_item_not_found` | Non-existent item → 404 | Missing items return 200 or 500 |
| `test_get_item_quotes_returns_200` | Quotes sub-resource returns array | Supplier quotes tab is broken |
| `test_get_item_inventory_returns_200` | Inventory sub-resource returns array | Inventory tab is broken |
| `test_get_item_receipts_returns_200` | Receipts sub-resource returns array | Receipt history tab is broken |
| `test_get_item_sales_returns_200` | Sales sub-resource returns array | Sale history tab is broken |
| `test_create_item_returns_201` | `POST /api/items/` returns 201 | **Item creation is broken** |
| `test_create_item_passes_data` | item_id and description are forwarded to service | Item data is lost or wrong |
| `test_update_item_returns_200` | `PUT /api/items/1` returns 200 | **Item update is broken** |
| `test_update_item_excludes_none_fields` | Only non-None fields are sent to service | Null fields overwrite real data |
| `test_delete_item_returns_success` | `DELETE /api/items/1` returns `{success: true}` | **Item deletion is broken** |

#### TestCategoryEndpoints (6 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_list_categories_returns_200` | Returns 200 with `{data, total}` | Category dropdown is broken |
| `test_list_categories_passes_default_pagination` | Default is `limit=5000, offset=0` | Default pagination changed |
| `test_list_categories_passes_custom_pagination` | Custom pagination forwarded | Custom pagination ignored |
| `test_create_category_returns_201` | Returns 201 with created category | Category creation is broken |
| `test_create_category_passes_data` | `{name}` is forwarded to service | Category data is lost |
| `test_delete_category_returns_success` | Returns `{success: true}` | Category deletion is broken |

#### TestLocationEndpoints (6 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_list_locations_returns_200` | Returns 200 with `{data, total}` | Location dropdown is broken |
| `test_list_locations_passes_default_pagination` | Default is `limit=5000, offset=0` | Default pagination changed |
| `test_list_locations_passes_custom_pagination` | Custom pagination forwarded | Custom pagination ignored |
| `test_create_location_returns_201` | Returns 201 with created location | Location creation is broken |
| `test_create_location_passes_data` | `{code}` is forwarded to service | Location data is lost |
| `test_delete_location_returns_success` | Returns `{success: true}` | Location deletion is broken |

#### TestSupplierEndpoints (5 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_list_suppliers_returns_200` | Returns 200 with `{data, total}` | Supplier dropdown is broken |
| `test_list_suppliers_passes_default_pagination` | Default is `limit=5000, offset=0` | Default pagination changed |
| `test_create_supplier_returns_201` | Returns 201 with created supplier | Supplier creation is broken |
| `test_create_supplier_passes_full_data` | Name, email, phone, address forwarded | Supplier data is lost |
| `test_delete_supplier_returns_success` | Returns `{success: true}` | Supplier deletion is broken |

#### TestCustomerEndpoints (5 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_list_customers_returns_200` | Returns 200 with `{data, total}` | Customer dropdown is broken |
| `test_list_customers_passes_default_pagination` | Default is `limit=5000, offset=0` | Default pagination changed |
| `test_list_customers_passes_custom_pagination` | Custom pagination forwarded | Custom pagination ignored |
| `test_create_customer_returns_201` | Returns 201 with created customer | Customer creation is broken |
| `test_create_customer_passes_full_data` | Name, email, phone, city forwarded | Customer data is lost |

#### TestChannelEndpoints (2 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_list_channels_returns_200` | Returns 200 with `{data, total}` | Channel dropdown is broken |
| `test_list_channels_passes_default_pagination` | Default is `limit=5000, offset=0` | Default pagination changed |

#### TestCurrencyEndpoints (2 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_list_currencies_returns_200` | Returns 200 with `{data, total}` | Currency dropdown is broken |
| `test_list_currencies_passes_default_pagination` | Default is `limit=5000, offset=0` | Default pagination changed |

#### TestInventoryEndpoints (7 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_list_movements_returns_200` | `GET /api/inventory/movements` returns 200 | Inventory movement log is broken |
| `test_list_movements_passes_default_pagination` | Default is `limit=50, offset=0` | Default pagination changed |
| `test_list_movements_passes_custom_pagination` | Custom pagination forwarded | Custom pagination ignored |
| `test_list_on_hand_returns_200` | `GET /api/inventory/on-hand` returns 200 with array | On-hand inventory is broken |
| `test_transfer_stock_returns_201` | `POST /api/inventory/transfer` returns 201 | **Stock transfers are broken** |
| `test_transfer_stock_passes_data_and_user_id` | from_stock_id, to_location_id, quantity, user_id, notes forwarded | Transfer data is lost or user_id missing |
| `test_transfer_stock_without_notes` | Transfer with no notes passes `None` | Transfer without notes crashes |

#### TestSupplierQuoteEndpoints (4 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_create_quote_returns_201` | `POST /api/supplier-quotes/` returns 201 | Quote creation is broken |
| `test_create_quote_excludes_note_field` | The `note` field is excluded from the service call | Note field leaks into repo data |
| `test_create_quote_passes_optional_datetime` | `date_time` is forwarded to service | Quote date is lost |
| `test_delete_quote_returns_success` | `DELETE /api/supplier-quotes/1` returns `{success: true}` | Quote deletion is broken |

#### TestUserEndpoints (4 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_get_me_returns_profile_dict` | `GET /api/users/me` returns `{user_id, first_name, last_name, email}` | **User profile endpoint is broken** |
| `test_get_me_no_profile_returns_404` | Returns 404 when user has no profile | Users without profiles cause a crash |
| `test_create_user_returns_201` | `POST /api/users/` returns 201 | User creation is broken |
| `test_create_user_passes_credentials` | Email and password forwarded to service | User credentials are lost |

#### TestHealthEndpoint (1 test)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_health_returns_200` | `GET /api/health` returns 200 with `status: "ok"` | App is not running |

---

### `test_auth_enforcement.py` (45 tests)

Every protected endpoint returns **401** when no Authorization header is provided. If any of these fail, a protected endpoint has lost its auth guard — **anyone on the internet can access it without logging in**.

#### TestSalesAuthEnforcement (5 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_list_sales_requires_auth` | `GET /api/sales/` → 401 | **Anyone can view all sales without logging in** |
| `test_get_sale_requires_auth` | `GET /api/sales/1` → 401 | **Anyone can view sale details without logging in** |
| `test_get_sale_lines_requires_auth` | `GET /api/sales/1/lines` → 401 | **Anyone can view sale line items without logging in** |
| `test_create_sale_requires_auth` | `POST /api/sales/` → 401 | **Anyone can create sales without logging in** |
| `test_void_sale_requires_auth` | `POST /api/sales/1/void` → 401 | **Anyone can void sales without logging in** |

#### TestReceiptsAuthEnforcement (5 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_list_receipts_requires_auth` | `GET /api/receipts/` → 401 | Anyone can view all receipts |
| `test_get_receipt_requires_auth` | `GET /api/receipts/1` → 401 | Anyone can view receipt details |
| `test_get_receipt_lines_requires_auth` | `GET /api/receipts/1/lines` → 401 | Anyone can view receipt lines |
| `test_create_receipt_requires_auth` | `POST /api/receipts/` → 401 | Anyone can create receipts |
| `test_void_receipt_requires_auth` | `POST /api/receipts/1/void` → 401 | Anyone can void receipts |

#### TestItemsAuthEnforcement (10 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_list_items_requires_auth` | `GET /api/items/` → 401 | Anyone can view all items |
| `test_search_items_requires_auth` | `GET /api/items/search?q=x` → 401 | Anyone can search items |
| `test_get_item_requires_auth` | `GET /api/items/1` → 401 | Anyone can view item details |
| `test_get_item_quotes_requires_auth` | `GET /api/items/1/quotes` → 401 | Anyone can view supplier quotes |
| `test_get_item_inventory_requires_auth` | `GET /api/items/1/inventory` → 401 | Anyone can view inventory levels |
| `test_get_item_receipts_requires_auth` | `GET /api/items/1/receipts` → 401 | Anyone can view receipt history |
| `test_get_item_sales_requires_auth` | `GET /api/items/1/sales` → 401 | Anyone can view sale history |
| `test_create_item_requires_auth` | `POST /api/items/` → 401 | Anyone can create items |
| `test_update_item_requires_auth` | `PUT /api/items/1` → 401 | Anyone can edit items |
| `test_delete_item_requires_auth` | `DELETE /api/items/1` → 401 | Anyone can delete items |

#### TestCategoriesAuthEnforcement (3 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_list_categories_requires_auth` | `GET /api/categories/` → 401 | Anyone can view categories |
| `test_create_category_requires_auth` | `POST /api/categories/` → 401 | Anyone can create categories |
| `test_delete_category_requires_auth` | `DELETE /api/categories/1` → 401 | Anyone can delete categories |

#### TestLocationsAuthEnforcement (3 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_list_locations_requires_auth` | `GET /api/locations/` → 401 | Anyone can view locations |
| `test_create_location_requires_auth` | `POST /api/locations/` → 401 | Anyone can create locations |
| `test_delete_location_requires_auth` | `DELETE /api/locations/1` → 401 | Anyone can delete locations |

#### TestSuppliersAuthEnforcement (3 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_list_suppliers_requires_auth` | `GET /api/suppliers/` → 401 | Anyone can view suppliers |
| `test_create_supplier_requires_auth` | `POST /api/suppliers/` → 401 | Anyone can create suppliers |
| `test_delete_supplier_requires_auth` | `DELETE /api/suppliers/1` → 401 | Anyone can delete suppliers |

#### TestCustomersAuthEnforcement (2 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_list_customers_requires_auth` | `GET /api/customers/` → 401 | Anyone can view customers |
| `test_create_customer_requires_auth` | `POST /api/customers/` → 401 | Anyone can create customers |

#### TestChannelsAuthEnforcement (1 test)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_list_channels_requires_auth` | `GET /api/channels/` → 401 | Anyone can view channels |

#### TestCurrenciesAuthEnforcement (1 test)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_list_currencies_requires_auth` | `GET /api/currencies/` → 401 | Anyone can view currencies |

#### TestInventoryAuthEnforcement (3 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_list_movements_requires_auth` | `GET /api/inventory/movements` → 401 | Anyone can view inventory movements |
| `test_list_on_hand_requires_auth` | `GET /api/inventory/on-hand` → 401 | Anyone can view stock levels |
| `test_transfer_stock_requires_auth` | `POST /api/inventory/transfer` → 401 | **Anyone can transfer stock without logging in** |

#### TestSupplierQuotesAuthEnforcement (2 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_create_quote_requires_auth` | `POST /api/supplier-quotes/` → 401 | Anyone can create quotes |
| `test_delete_quote_requires_auth` | `DELETE /api/supplier-quotes/1` → 401 | Anyone can delete quotes |

#### TestUsersAuthEnforcement (2 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_get_me_requires_auth` | `GET /api/users/me` → 401 | Anyone can view user profiles |
| `test_create_user_requires_auth` | `POST /api/users/` → 401 | **Anyone can create user accounts without logging in** |

#### TestAuthProtectedEndpoints (2 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_get_auth_me_requires_auth` | `GET /api/auth/me` → 401 | Anyone can view auth identity |
| `test_change_password_requires_auth` | `POST /api/auth/change-password` → 401 | **Anyone can change passwords without logging in** |

#### TestPublicEndpoints (3 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_health_is_public` | `GET /api/health` returns 200 without auth | Health check requires auth — monitoring will break |
| `test_login_is_public` | `POST /api/auth/login` works without auth | Login requires auth — nobody can log in |
| `test_signup_is_public` | `POST /api/auth/signup` works without auth | Signup requires auth — nobody can register |

---

### `test_response_contracts.py` (30 tests)

Verifies the exact JSON shape the frontend depends on. If any of these fail, **the frontend will break** because it parses the response with specific key expectations.

#### TestSalesContract (6 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_list_sales_returns_paginated_with_sale_objects` | `GET /api/sales/` returns `{data: [{sale_id, status, created_at, ...}], total: N}` | **Sales page shows no data** — the frontend expects `data` and `total` keys |
| `test_list_sales_empty_returns_paginated_zero` | Empty result returns `{data: [], total: 0}` | Empty sales page crashes instead of showing "no results" |
| `test_get_sale_returns_sale_object` | Single sale has `sale_id`, `status`, `created_at` | Sale detail page crashes |
| `test_get_sale_lines_returns_list` | Lines endpoint returns an array with `quantity`, `unit_price` | Sale line items don't render |
| `test_create_sale_returns_object_with_sale_id` | Create returns object with `sale_id` | Frontend can't navigate to the new sale after creation |
| `test_void_sale_returns_success_flag` | Void returns `{success: true}` | Void appears to fail even when it succeeds |

#### TestReceiptsContract (4 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_list_receipts_returns_paginated` | Returns `{data: [{receipt_id, status, created_at}], total: N}` | **Receipts page shows no data** |
| `test_get_receipt_returns_receipt_object` | Single receipt has `receipt_id`, `status`, `created_at` | Receipt detail page crashes |
| `test_get_receipt_lines_returns_list` | Lines endpoint returns an array | Receipt line items don't render |
| `test_void_receipt_returns_success_flag` | Void returns `{success: true}` | Void appears to fail |

#### TestItemsContract (4 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_list_items_returns_paginated` | Returns `{data: [{id, item_id}], total: N}` | **Items page shows no data** |
| `test_search_items_returns_paginated` | Search returns `{data, total}` | Item search results don't render |
| `test_get_item_returns_item_object` | Single item has `id`, `item_id` | Item detail page crashes |
| `test_delete_item_returns_success_flag` | Delete returns `{success: true}` | Delete appears to fail |

#### TestAuthMeContract (2 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_auth_me_with_profile_has_correct_shape` | Returns `{user: {id, email}, profile: {user_id, name, email_address}}` | **The navigation bar can't show the user's name** — the frontend reads `profile.name` |
| `test_auth_me_without_profile_returns_null_profile` | Returns `{user: {id, email}, profile: null}` | Users without profiles crash the frontend |

#### TestUsersMeContract (1 test)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_users_me_returns_profile_fields` | Returns `{user_id: int, first_name, last_name, email}` | Settings page crashes |

#### TestLookupEntityContracts (6 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_categories_list_is_paginated` | `GET /api/categories/` returns `{data, total}` | Category dropdown is broken |
| `test_locations_list_is_paginated` | `GET /api/locations/` returns `{data, total}` | Location dropdown is broken |
| `test_suppliers_list_is_paginated` | `GET /api/suppliers/` returns `{data, total}` | Supplier dropdown is broken |
| `test_customers_list_is_paginated` | `GET /api/customers/` returns `{data, total}` | Customer dropdown is broken |
| `test_channels_list_is_paginated` | `GET /api/channels/` returns `{data, total}` | Channel dropdown is broken |
| `test_currencies_list_is_paginated` | `GET /api/currencies/` returns `{data, total}` | Currency dropdown is broken |

#### TestInventoryContract (2 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_movements_is_paginated` | `GET /api/inventory/movements` returns `{data, total}` | Movement log is broken |
| `test_on_hand_is_plain_array` | `GET /api/inventory/on-hand` returns a plain array (not `{data, total}`) | On-hand view crashes — it expects an array, not a paginated object |

#### TestDeleteVoidContracts (5 tests)

| Test | What it tests | If this fails |
|------|---------------|---------------|
| `test_delete_category_contract` | `DELETE /api/categories/1` returns `{success: true}` | Frontend thinks delete failed |
| `test_delete_location_contract` | `DELETE /api/locations/1` returns `{success: true}` | Frontend thinks delete failed |
| `test_delete_supplier_contract` | `DELETE /api/suppliers/1` returns `{success: true}` | Frontend thinks delete failed |
| `test_delete_supplier_quote_contract` | `DELETE /api/supplier-quotes/1` returns `{success: true}` | Frontend thinks delete failed |
| `test_delete_item_contract` | `DELETE /api/items/1` returns `{success: true}` | Frontend thinks delete failed |

---

## eBay Tests (61 tests)

See `tests/ebay/README.md` for full documentation.

| File | Tests | What it covers |
|------|-------|----------------|
| `test_ebay_client.py` | 18 | Consent URL, token exchange/refresh, `get_orders`, `get_all_orders`, `get_valid_access_token` |
| `test_ebay_routers.py` | 16 | `/auth`, `/callback`, `/token`, `/status`, `/sync`, `/sync/history`, purge preview/delete |
| `test_ebay_schemas.py` | 8 | `SOURCE_TAG`, order/line/token fixture shapes |
| `test_ebay_sync.py` | 19 | `IsPaid`, `SyncOrders`, `ResolveCustomer`, `ResolveItem` |

---

## `conftest.py` — Shared Fixtures

| Fixture | Purpose |
|---------|---------|
| `client` | Unauthenticated `TestClient` — no auth override |
| `mock_user` | `CurrentUser` with full `UserProfile` (user_id=456) |
| `mock_user_no_profile` | `CurrentUser` with `profile=None` |
| `authed_client` | `TestClient` with `get_current_user` overridden to `mock_user` |
| `unauthed_client` | `TestClient` with `get_current_user` overridden to profileless user |

Auth is overridden via `app.dependency_overrides` so tests never contact Supabase.

---

## CI Enforcement

The test suite is enforced in `.github/workflows/ci.yml`:

```yaml
- name: Unit tests with coverage
  run: pytest --tb=short -q --cov=app --cov-report=term-missing --cov-fail-under=60
```

**What this blocks:**

| Scenario | How CI catches it |
|----------|-------------------|
| Endpoint returns wrong data shape | `test_response_contracts.py` fails |
| Endpoint stops returning data | `test_router_responses.py` fails |
| Auth guard removed from endpoint | `test_auth_enforcement.py` fails |
| Bad input no longer rejected | `test_routers.py` fails |
| Service logic broken | `test_services.py` fails |
| Schema validation weakened | `test_schemas.py` fails |
| Coverage drops below 60% | `--cov-fail-under=60` blocks merge |

**Branch protection** (set in GitHub UI) requires the `test` job to pass before merging to `main`.

---

## Running Tests

```bash
pip install -r requirements.txt -r requirements-dev.txt

pytest --tb=short -q                                         # all tests
pytest tests/test_router_responses.py -v                     # happy-path suite
pytest tests/test_auth_enforcement.py -v                     # auth guard tests
pytest tests/test_response_contracts.py -v                   # contract tests
pytest tests/test_services.py::TestSaleServiceSearch -v      # single class
pytest tests/ebay/ -v                                        # all eBay tests
pytest --cov=app --cov-report=html                           # coverage report
```
