from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.ebay import client as ebay_client


class TestGetConsentUrl:
    def test_generates_valid_consent_url(self):
        url = ebay_client.get_consent_url()
        assert "auth.sandbox.ebay.com" in url
        assert "test-ebay-client-id" in url
        assert "response_type=code" in url
        assert "sell.fulfillment.readonly" in url
        assert "test-ebay-ru-name" in url


class TestExchangeCodeForToken:
    @patch("app.ebay.client.httpx.post")
    def test_successful_exchange(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "access_token": "v^1.1#new_access",
                "refresh_token": "v^1.1#new_refresh",
                "expires_in": 7200,
                "token_type": "User Access Token",
            },
            raise_for_status=lambda: None,
        )

        result = ebay_client.exchange_code_for_token("test_auth_code")

        assert result["access_token"] == "v^1.1#new_access"
        assert result["refresh_token"] == "v^1.1#new_refresh"
        assert result["expires_in"] == 7200

        call_kwargs = mock_post.call_args
        assert "authorization_code" in str(call_kwargs)
        assert "test_auth_code" in str(call_kwargs)

    @patch("app.ebay.client.httpx.post")
    def test_exchange_sends_basic_auth(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "access_token": "tok",
                "refresh_token": "ref",
                "expires_in": 7200,
            },
            raise_for_status=lambda: None,
        )

        ebay_client.exchange_code_for_token("code123")

        headers = mock_post.call_args.kwargs.get("headers", {})
        assert "Basic" in headers.get("Authorization", "")

    @patch("app.ebay.client.httpx.post")
    def test_exchange_raises_on_http_error(self, mock_post):
        response = httpx.Response(status_code=401, request=httpx.Request("POST", "http://test"))
        mock_post.return_value = response

        with pytest.raises(httpx.HTTPStatusError):
            ebay_client.exchange_code_for_token("bad_code")


class TestRefreshAccessToken:
    @patch("app.ebay.client.httpx.post")
    def test_successful_refresh(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "access_token": "v^1.1#refreshed_access",
                "expires_in": 7200,
            },
            raise_for_status=lambda: None,
        )

        result = ebay_client.refresh_access_token("old_refresh_token")

        assert result["access_token"] == "v^1.1#refreshed_access"
        assert result["expires_in"] == 7200

    @patch("app.ebay.client.httpx.post")
    def test_refresh_raises_on_error(self, mock_post):
        response = httpx.Response(status_code=500, request=httpx.Request("POST", "http://test"))
        mock_post.return_value = response

        with pytest.raises(httpx.HTTPStatusError):
            ebay_client.refresh_access_token("bad_refresh")


class TestGetOrders:
    @patch("app.ebay.client.httpx.get")
    def test_successful_fetch(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "orders": [{"orderId": "111"}],
                "total": 1,
            },
            raise_for_status=lambda: None,
        )

        result = ebay_client.get_orders("access_tok")

        assert result["total"] == 1
        assert len(result["orders"]) == 1

    @patch("app.ebay.client.httpx.get")
    def test_passes_date_filter(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"orders": [], "total": 0},
            raise_for_status=lambda: None,
        )

        ebay_client.get_orders("tok", date_from="2026-01-01T00:00:00Z")

        params = mock_get.call_args.kwargs.get("params", {})
        assert "creationdate:" in params.get("filter", "")

    @patch("app.ebay.client.httpx.get")
    def test_passes_pagination(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"orders": [], "total": 0},
            raise_for_status=lambda: None,
        )

        ebay_client.get_orders("tok", limit=50, offset=100)

        params = mock_get.call_args.kwargs.get("params", {})
        assert params["limit"] == 50
        assert params["offset"] == 100

    @patch("app.ebay.client.httpx.get")
    def test_raises_on_401(self, mock_get):
        response = httpx.Response(status_code=401, request=httpx.Request("GET", "http://test"))
        mock_get.return_value = response

        with pytest.raises(httpx.HTTPStatusError):
            ebay_client.get_orders("bad_token")


class TestGetAllOrders:
    @patch("app.ebay.client.get_orders")
    def test_single_page(self, mock_get_orders):
        mock_get_orders.return_value = {
            "orders": [{"orderId": "1"}, {"orderId": "2"}],
            "total": 2,
        }

        result = ebay_client.get_all_orders("tok")
        assert len(result) == 2

    @patch("app.ebay.client.get_orders")
    def test_multiple_pages(self, mock_get_orders):
        mock_get_orders.side_effect = [
            {"orders": [{"orderId": str(i)} for i in range(200)], "total": 350},
            {"orders": [{"orderId": str(i)} for i in range(200, 350)], "total": 350},
        ]

        result = ebay_client.get_all_orders("tok")
        assert len(result) == 350

    @patch("app.ebay.client.get_orders")
    def test_empty_result(self, mock_get_orders):
        mock_get_orders.return_value = {"orders": [], "total": 0}

        result = ebay_client.get_all_orders("tok")
        assert result == []


class TestGetValidAccessToken:
    def test_returns_none_when_no_token(self):
        repo = MagicMock()
        repo.get_current.return_value = None

        result = ebay_client.get_valid_access_token(repo)
        assert result is None

    def test_returns_token_when_not_expired(self, mock_ebay_token):
        repo = MagicMock()
        repo.get_current.return_value = mock_ebay_token

        result = ebay_client.get_valid_access_token(repo)
        assert result == mock_ebay_token["access_token"]

    @patch("app.ebay.client.refresh_access_token")
    def test_refreshes_when_expired(self, mock_refresh, mock_ebay_token):
        mock_ebay_token["token_expiry"] = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

        repo = MagicMock()
        repo.get_current.return_value = mock_ebay_token

        mock_refresh.return_value = {
            "access_token": "new_access",
            "expires_in": 7200,
        }

        result = ebay_client.get_valid_access_token(repo)

        assert result == "new_access"
        repo.update_access_token.assert_called_once()
        mock_refresh.assert_called_once_with(mock_ebay_token["refresh_token"])
