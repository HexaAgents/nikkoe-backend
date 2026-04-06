import pytest


@pytest.fixture
def sample_ebay_order():
    """A realistic single-line eBay Fulfillment API order."""
    return {
        "orderId": "12-34567-89012",
        "creationDate": "2026-03-15T10:30:00.000Z",
        "orderPaymentStatus": "PAID",
        "orderFulfillmentStatus": "FULFILLED",
        "buyer": {
            "username": "test_buyer_42",
        },
        "pricingSummary": {
            "total": {"value": "29.99", "currency": "GBP"},
        },
        "lineItems": [
            {
                "lineItemId": "8000000000001",
                "title": "Vintage Widget Model A",
                "sku": "WIDGET-A-001",
                "quantity": 1,
                "total": {"value": "29.99", "currency": "GBP"},
                "legacyItemId": "110123456789",
            }
        ],
        "fulfillmentStartInstructions": [
            {
                "shippingStep": {
                    "shipTo": {
                        "contactAddress": {
                            "addressLine1": "123 Test Street",
                            "city": "London",
                            "countryCode": "GB",
                            "postalCode": "SW1A 1AA",
                        }
                    }
                }
            }
        ],
    }


@pytest.fixture
def sample_ebay_order_multi_line():
    """An eBay order with multiple line items."""
    return {
        "orderId": "12-34567-89099",
        "creationDate": "2026-03-16T14:00:00.000Z",
        "orderPaymentStatus": "PAID",
        "orderFulfillmentStatus": "FULFILLED",
        "buyer": {
            "username": "multi_buyer_99",
        },
        "pricingSummary": {
            "total": {"value": "75.00", "currency": "USD"},
        },
        "lineItems": [
            {
                "lineItemId": "8000000000010",
                "title": "Gadget X",
                "sku": "GADGET-X",
                "quantity": 2,
                "total": {"value": "50.00", "currency": "USD"},
                "legacyItemId": "110987654321",
            },
            {
                "lineItemId": "8000000000011",
                "title": "Accessory Y",
                "sku": "ACC-Y",
                "quantity": 1,
                "total": {"value": "25.00", "currency": "USD"},
                "legacyItemId": "110987654322",
            },
        ],
        "fulfillmentStartInstructions": [],
    }


@pytest.fixture
def sample_unpaid_order():
    """An eBay order that is not yet paid."""
    return {
        "orderId": "12-00000-00001",
        "creationDate": "2026-03-17T09:00:00.000Z",
        "orderPaymentStatus": "PENDING",
        "orderFulfillmentStatus": "NOT_STARTED",
        "buyer": {"username": "unpaid_buyer"},
        "lineItems": [],
        "fulfillmentStartInstructions": [],
    }


@pytest.fixture
def mock_ebay_token():
    """A stored eBay token dict as it would come from the database."""
    return {
        "id": 1,
        "ebay_user_id": "testuser",
        "access_token": "v^1.1#fake_access_token",
        "refresh_token": "v^1.1#fake_refresh_token",
        "token_expiry": "2026-12-31T23:59:59+00:00",
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }
