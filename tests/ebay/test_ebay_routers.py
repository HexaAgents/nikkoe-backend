from unittest.mock import MagicMock, patch


class TestEbayAuth:
    def test_returns_valid_consent_url(self, authed_client):
        resp = authed_client.get("/api/ebay/auth")
        assert resp.status_code == 200
        url = resp.json()["consent_url"]
        assert "auth.sandbox.ebay.com" in url
        assert "test-ebay-client-id" in url
        assert "sell.fulfillment.readonly" in url

    def test_requires_auth(self, client):
        resp = client.get("/api/ebay/auth")
        assert resp.status_code == 401


class TestEbayCallback:
    @patch("app.routers.ebay.ebay_client.exchange_code_for_token")
    @patch("app.routers.ebay.token_repo")
    def test_successful_callback(self, mock_repo, mock_exchange, authed_client):
        mock_exchange.return_value = {
            "access_token": "new_access",
            "refresh_token": "new_refresh",
            "expires_in": 7200,
        }

        resp = authed_client.get("/api/ebay/callback?code=test_code_123")
        assert resp.status_code == 200
        assert "linked" in resp.json()["message"].lower()

    @patch("app.routers.ebay.ebay_client.exchange_code_for_token")
    def test_invalid_code_returns_400(self, mock_exchange, authed_client):
        mock_exchange.side_effect = Exception("invalid_grant")

        resp = authed_client.get("/api/ebay/callback?code=bad_code")
        assert resp.status_code == 400
        assert "failed" in resp.json()["error"].lower()

    def test_missing_code_returns_422(self, authed_client):
        resp = authed_client.get("/api/ebay/callback")
        assert resp.status_code == 422


class TestEbayManualToken:
    @patch("app.routers.ebay.ebay_client.exchange_code_for_token")
    @patch("app.routers.ebay.token_repo")
    def test_successful_manual_exchange(self, mock_repo, mock_exchange, authed_client):
        mock_exchange.return_value = {
            "access_token": "manual_access",
            "refresh_token": "manual_refresh",
            "expires_in": 7200,
        }

        resp = authed_client.post("/api/ebay/token?code=manual_code")
        assert resp.status_code == 200
        assert "linked" in resp.json()["message"].lower()

    def test_requires_auth(self, client):
        resp = client.post("/api/ebay/token?code=test")
        assert resp.status_code == 401


class TestEbayStatus:
    @patch("app.routers.ebay.sync_log_repo")
    @patch("app.routers.ebay.token_repo")
    def test_not_linked(self, mock_token_repo, mock_sync_repo, authed_client):
        mock_token_repo.get_current.return_value = None

        resp = authed_client.get("/api/ebay/status")
        assert resp.status_code == 200
        assert resp.json()["linked"] is False

    @patch("app.routers.ebay.sync_log_repo")
    @patch("app.routers.ebay.token_repo")
    def test_linked_with_token(self, mock_token_repo, mock_sync_repo, authed_client, mock_ebay_token):
        mock_token_repo.get_current.return_value = mock_ebay_token
        mock_sync_repo.get_last_successful.return_value = None

        resp = authed_client.get("/api/ebay/status")
        data = resp.json()
        assert data["linked"] is True
        assert data["ebay_user_id"] == "testuser"

    def test_requires_auth(self, client):
        resp = client.get("/api/ebay/status")
        assert resp.status_code == 401


class TestTriggerSync:
    @patch("app.routers.ebay.sync_service")
    def test_triggers_sync(self, mock_svc, authed_client):
        mock_svc.sync_orders.return_value = {
            "orders_fetched": 5,
            "orders_imported": 3,
            "orders_skipped": 2,
        }

        resp = authed_client.post("/api/ebay/sync")
        assert resp.status_code == 200
        data = resp.json()
        assert data["orders_imported"] == 3

    @patch("app.routers.ebay.sync_service")
    def test_accepts_date_from(self, mock_svc, authed_client):
        mock_svc.sync_orders.return_value = {}

        resp = authed_client.post("/api/ebay/sync?date_from=2026-01-01T00:00:00Z")
        assert resp.status_code == 200
        mock_svc.sync_orders.assert_called_once_with(date_from="2026-01-01T00:00:00Z")

    def test_requires_auth(self, client):
        resp = client.post("/api/ebay/sync")
        assert resp.status_code == 401


class TestSyncHistory:
    @patch("app.routers.ebay.sync_log_repo")
    def test_returns_history(self, mock_repo, authed_client):
        mock_repo.list_recent.return_value = [
            {"id": 1, "status": "SUCCESS", "orders_imported": 10},
            {"id": 2, "status": "FAILED", "error_message": "timeout"},
        ]

        resp = authed_client.get("/api/ebay/sync/history")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    def test_requires_auth(self, client):
        resp = client.get("/api/ebay/sync/history")
        assert resp.status_code == 401


class TestPurgePreview:
    @patch("app.routers.ebay.supabase")
    def test_returns_counts(self, mock_sb, authed_client):
        select_mock = MagicMock()
        select_mock.eq.return_value = select_mock
        select_mock.limit.return_value = select_mock
        select_mock.execute.return_value = MagicMock(count=5)
        mock_sb.table.return_value = MagicMock(select=MagicMock(return_value=select_mock))

        resp = authed_client.get("/api/ebay/purge/preview")
        assert resp.status_code == 200
        data = resp.json()
        assert "counts" in data
        assert data["source"] == "EBAY_IMPORT"

    def test_requires_auth(self, client):
        resp = client.get("/api/ebay/purge/preview")
        assert resp.status_code == 401


class TestPurge:
    @patch("app.routers.ebay.token_repo")
    @patch("app.routers.ebay.supabase")
    def test_deletes_data(self, mock_sb, mock_token_repo, authed_client):
        select_mock = MagicMock()
        select_mock.eq.return_value = select_mock
        select_mock.limit.return_value = select_mock
        select_mock.execute.return_value = MagicMock(count=3)

        delete_mock = MagicMock()
        delete_mock.eq.return_value = delete_mock
        delete_mock.execute.return_value = MagicMock(data=[])

        table_mock = MagicMock()
        table_mock.select.return_value = select_mock
        table_mock.delete.return_value = delete_mock
        mock_sb.table.return_value = table_mock

        resp = authed_client.delete("/api/ebay/purge")
        assert resp.status_code == 200
        data = resp.json()
        assert "deleted" in data
        assert "purged" in data["message"].lower()

    def test_requires_auth(self, client):
        resp = client.delete("/api/ebay/purge")
        assert resp.status_code == 401
