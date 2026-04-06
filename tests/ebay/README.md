# eBay Integration Tests

Tests for the eBay OAuth flow, API client, sync service, and HTTP endpoints. All tests use mocked HTTP calls and mocked Supabase — no real eBay API or database connections.

---

## Fixtures (`conftest.py`)

| Fixture | Description |
|---------|-------------|
| `sample_ebay_order` | Single-line paid eBay order (GBP, 1 item) |
| `sample_ebay_order_multi_line` | Multi-line paid order (USD, 2 items) |
| `sample_unpaid_order` | Unpaid order with empty line items |
| `mock_ebay_token` | Stored token dict as returned from database |

These fixtures also inherit all root-level fixtures (`client`, `authed_client`, `unauthed_client`, `mock_user`).

---

## Test Cases by File

### `test_ebay_client.py` (12 tests)

Tests the low-level eBay API client functions in `app/ebay/client.py`.

| Class | Tests | What it verifies |
|-------|-------|-----------------|
| `TestGetConsentUrl` | 1 | Generated URL contains sandbox base, client ID, response_type, scopes, and RU name |
| `TestExchangeCodeForToken` | 3 | Successful exchange returns tokens; sends Basic auth header; raises on HTTP error |
| `TestRefreshAccessToken` | 2 | Successful refresh returns new access token; raises on HTTP error |
| `TestGetOrders` | 4 | Successful fetch; passes date filter; passes pagination params; raises on 401 |
| `TestGetAllOrders` | 3 | Single page; auto-paginates multiple pages; handles empty result |
| `TestGetValidAccessToken` | 3 | Returns None when no token; returns token when valid; refreshes when expired |

### `test_ebay_routers.py` (16 tests)

Tests eBay HTTP endpoints via TestClient.

| Class | Tests | What it verifies |
|-------|-------|-----------------|
| `TestEbayAuth` | 2 | Returns valid consent URL with correct components; requires auth |
| `TestEbayCallback` | 3 | Successful callback stores token; invalid code returns 400; missing code returns 422 |
| `TestEbayManualToken` | 2 | Manual code exchange works; requires auth |
| `TestEbayStatus` | 3 | Not-linked returns `linked: false`; linked shows user ID; requires auth |
| `TestTriggerSync` | 3 | Triggers sync and returns counts; accepts date_from filter; requires auth |
| `TestSyncHistory` | 2 | Returns history list; requires auth |
| `TestPurgePreview` | 2 | Returns counts with source tag; requires auth |
| `TestPurge` | 2 | Deletes eBay-imported data; requires auth |

### `test_ebay_schemas.py` (8 tests)

Validates the shape of test fixtures and constants used across eBay tests.

| Class | Tests | What it verifies |
|-------|-------|-----------------|
| `TestSourceTag` | 1 | `SOURCE_TAG == "EBAY_IMPORT"` |
| `TestOrderFixtureShape` | 5 | Single order has required fields; line items have required fields; multi-line order; unpaid status; shipping address shape |
| `TestTokenFixtureShape` | 2 | Token has required fields; expiry is parseable ISO string |

### `test_ebay_sync.py` (11 tests)

Tests the `EbaySyncService` business logic with mocked dependencies.

| Class | Tests | What it verifies |
|-------|-------|-----------------|
| `TestIsPaid` | 4 | PAID→true; PARTIALLY_REFUNDED→true; PENDING→false; missing status→false |
| `TestSyncOrders` | 6 | No token returns error; skips unpaid; skips already-imported; imports paid order (full flow); logs failure on exception; uses last sync timestamp |
| `TestResolveCustomer` | 3 | Returns None for no buyer; finds existing customer; creates new customer with source tag |
| `TestResolveItem` | 3 | Returns None for empty SKU; finds existing item; creates item with source tag |

---

## Running eBay Tests Only

```bash
pytest tests/ebay/ -v
pytest tests/ebay/test_ebay_sync.py::TestSyncOrders -v    # single class
```
