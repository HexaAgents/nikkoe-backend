"""Tests for eBay-related data shape validation.

Since the eBay integration uses plain dicts (not Pydantic models) for most data,
these tests validate the shape of data structures produced by the sync service
and expected by the API endpoints.
"""

from app.services.ebay_sync import SOURCE_TAG


class TestSourceTag:
    def test_source_tag_value(self):
        assert SOURCE_TAG == "EBAY_IMPORT"


class TestOrderFixtureShape:
    """Validate that our test fixtures match the eBay API response shape."""

    def test_single_order_has_required_fields(self, sample_ebay_order):
        assert "orderId" in sample_ebay_order
        assert "creationDate" in sample_ebay_order
        assert "orderPaymentStatus" in sample_ebay_order
        assert "buyer" in sample_ebay_order
        assert "lineItems" in sample_ebay_order
        assert isinstance(sample_ebay_order["lineItems"], list)

    def test_line_item_has_required_fields(self, sample_ebay_order):
        line = sample_ebay_order["lineItems"][0]
        assert "title" in line
        assert "sku" in line
        assert "quantity" in line
        assert "total" in line
        assert "value" in line["total"]
        assert "currency" in line["total"]

    def test_multi_line_order(self, sample_ebay_order_multi_line):
        assert len(sample_ebay_order_multi_line["lineItems"]) == 2

    def test_unpaid_order_status(self, sample_unpaid_order):
        assert sample_unpaid_order["orderPaymentStatus"] == "PENDING"

    def test_buyer_has_username(self, sample_ebay_order):
        assert "username" in sample_ebay_order["buyer"]

    def test_shipping_address_shape(self, sample_ebay_order):
        instructions = sample_ebay_order["fulfillmentStartInstructions"]
        assert len(instructions) > 0
        address = instructions[0]["shippingStep"]["shipTo"]["contactAddress"]
        assert "addressLine1" in address
        assert "city" in address
        assert "countryCode" in address
        assert "postalCode" in address


class TestTokenFixtureShape:
    def test_token_has_required_fields(self, mock_ebay_token):
        assert "id" in mock_ebay_token
        assert "access_token" in mock_ebay_token
        assert "refresh_token" in mock_ebay_token
        assert "token_expiry" in mock_ebay_token

    def test_token_expiry_is_iso_string(self, mock_ebay_token):
        from datetime import datetime

        datetime.fromisoformat(mock_ebay_token["token_expiry"])
