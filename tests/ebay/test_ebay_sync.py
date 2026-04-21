from unittest.mock import MagicMock, patch

from app.services.ebay_sync import SOURCE_TAG, EbaySyncService


def _make_service(token_repo=None, sync_log_repo=None):
    return EbaySyncService(
        token_repo=token_repo or MagicMock(),
        sync_log_repo=sync_log_repo or MagicMock(),
    )


class TestIsPaid:
    def test_paid_order(self):
        svc = _make_service()
        assert svc._is_paid({"orderPaymentStatus": "PAID"}) is True

    def test_partially_refunded(self):
        svc = _make_service()
        assert svc._is_paid({"orderPaymentStatus": "PARTIALLY_REFUNDED"}) is True

    def test_pending_order(self):
        svc = _make_service()
        assert svc._is_paid({"orderPaymentStatus": "PENDING"}) is False

    def test_missing_status(self):
        svc = _make_service()
        assert svc._is_paid({}) is False


class TestSyncOrders:
    @patch("app.services.ebay_sync.ebay_client")
    @patch("app.services.ebay_sync.supabase")
    def test_no_token_returns_error(self, mock_sb, mock_client):
        sync_log = MagicMock()
        sync_log.create.return_value = {"id": 1}

        token_repo = MagicMock()
        mock_client.get_valid_access_token.return_value = None

        svc = _make_service(token_repo=token_repo, sync_log_repo=sync_log)
        result = svc.sync_orders()

        assert result.get("error") == "No eBay token linked"
        sync_log.fail.assert_called_once()

    @patch("app.services.ebay_sync.ebay_client")
    @patch("app.services.ebay_sync.supabase")
    def test_skips_unpaid_orders(self, mock_sb, mock_client, sample_unpaid_order):
        sync_log = MagicMock()
        sync_log.create.return_value = {"id": 1}
        sync_log.get_last_successful.return_value = None
        sync_log.complete.return_value = {
            "orders_fetched": 1,
            "orders_imported": 0,
            "orders_skipped": 1,
        }

        mock_client.get_valid_access_token.return_value = "tok"
        mock_client.get_all_orders.return_value = [sample_unpaid_order]

        svc = _make_service(sync_log_repo=sync_log)
        svc.sync_orders()

        sync_log.complete.assert_called_once()
        call_kwargs = sync_log.complete.call_args
        assert call_kwargs.kwargs["orders_skipped"] == 1
        assert call_kwargs.kwargs["orders_imported"] == 0

    @patch("app.services.ebay_sync.ebay_client")
    @patch("app.services.ebay_sync.supabase")
    def test_skips_already_imported(self, mock_sb, mock_client, sample_ebay_order):
        sync_log = MagicMock()
        sync_log.create.return_value = {"id": 1}
        sync_log.get_last_successful.return_value = None
        sync_log.complete.return_value = {"orders_fetched": 1, "orders_imported": 0, "orders_skipped": 1}

        mock_client.get_valid_access_token.return_value = "tok"
        mock_client.get_all_orders.return_value = [sample_ebay_order]

        # Simulate that the order already exists
        sale_select = MagicMock()
        sale_select.eq.return_value = sale_select
        sale_select.limit.return_value = sale_select
        sale_select.execute.return_value = MagicMock(data=[{"id": 999}])
        mock_sb.table.return_value = MagicMock(select=MagicMock(return_value=sale_select))

        svc = _make_service(sync_log_repo=sync_log)
        svc.sync_orders()

        sync_log.complete.assert_called_once()
        assert sync_log.complete.call_args.kwargs["orders_skipped"] == 1

    @patch("app.services.ebay_sync.ebay_client")
    @patch("app.services.ebay_sync.supabase")
    def test_imports_paid_order(self, mock_sb, mock_client, sample_ebay_order):
        sync_log = MagicMock()
        sync_log.create.return_value = {"id": 1}
        sync_log.get_last_successful.return_value = None
        sync_log.complete.return_value = {"orders_fetched": 1, "orders_imported": 1, "orders_skipped": 0}

        mock_client.get_valid_access_token.return_value = "tok"
        mock_client.get_all_orders.return_value = [sample_ebay_order]

        svc = _make_service(sync_log_repo=sync_log)

        # Stub internal helpers to bypass complex Supabase chaining
        svc._already_imported = lambda order: False
        svc._get_ebay_channel_id = lambda: 5
        svc._get_ebay_location_id = lambda: 10
        svc._resolve_customer = lambda order: 20
        svc._resolve_item = lambda sku, title: 30
        svc._resolve_stock = lambda item_id, loc_id: 40
        svc._resolve_currency = lambda code: 1

        # Mock Sale insert + Sale_Stock insert + Stock quantity update
        sale_insert = MagicMock()
        sale_insert.execute.return_value = MagicMock(data=[{"id": 100, "source": SOURCE_TAG}])

        stock_select = MagicMock()
        stock_select.eq.return_value = stock_select
        stock_select.single.return_value = stock_select
        stock_select.execute.return_value = MagicMock(data={"quantity": 10})

        stock_update = MagicMock()
        stock_update.eq.return_value = stock_update
        stock_update.execute.return_value = MagicMock(data=[])

        line_insert = MagicMock()
        line_insert.execute.return_value = MagicMock(data=[{"id": 50}])

        def table_side_effect(name):
            mock_table = MagicMock()
            if name == "sale":
                mock_table.insert.return_value = sale_insert
            elif name == "sale_stock":
                mock_table.insert.return_value = line_insert
            elif name == "stock":
                mock_table.select.return_value = stock_select
                mock_table.update.return_value = stock_update
            return mock_table

        mock_sb.table.side_effect = table_side_effect

        svc.sync_orders()

        sync_log.complete.assert_called_once()
        assert sync_log.complete.call_args.kwargs["orders_imported"] == 1

    @patch("app.services.ebay_sync.ebay_client")
    @patch("app.services.ebay_sync.supabase")
    def test_sync_failure_logs_error(self, mock_sb, mock_client):
        sync_log = MagicMock()
        sync_log.create.return_value = {"id": 1}
        sync_log.get_last_successful.return_value = None

        mock_client.get_valid_access_token.return_value = "tok"
        mock_client.get_all_orders.side_effect = Exception("API down")

        svc = _make_service(sync_log_repo=sync_log)
        result = svc.sync_orders()

        assert "error" in result
        sync_log.fail.assert_called_once()
        assert "API down" in sync_log.fail.call_args[0][1]

    @patch("app.services.ebay_sync.ebay_client")
    @patch("app.services.ebay_sync.supabase")
    def test_uses_last_sync_timestamp(self, mock_sb, mock_client):
        sync_log = MagicMock()
        sync_log.create.return_value = {"id": 1}
        sync_log.get_last_successful.return_value = {"sync_to": "2026-03-01T00:00:00+00:00"}
        sync_log.complete.return_value = {}

        mock_client.get_valid_access_token.return_value = "tok"
        mock_client.get_all_orders.return_value = []

        svc = _make_service(sync_log_repo=sync_log)
        svc.sync_orders()

        mock_client.get_all_orders.assert_called_once_with("tok", date_from="2026-03-01T00:00:00+00:00")

    @patch("app.services.ebay_sync.ebay_client")
    @patch("app.services.ebay_sync.supabase")
    def test_filters_only_paid(self, mock_sb, mock_client, sample_ebay_order, sample_unpaid_order):
        sync_log = MagicMock()
        sync_log.create.return_value = {"id": 1}
        sync_log.get_last_successful.return_value = None
        sync_log.complete.return_value = {}

        mock_client.get_valid_access_token.return_value = "tok"
        mock_client.get_all_orders.return_value = [sample_ebay_order, sample_unpaid_order]

        svc = _make_service(sync_log_repo=sync_log)

        svc._already_imported = lambda order: False
        svc._get_ebay_channel_id = lambda: 5
        svc._get_ebay_location_id = lambda: 10
        svc._resolve_customer = lambda order: 20
        svc._resolve_item = lambda sku, title: 30
        svc._resolve_stock = lambda item_id, loc_id: 40
        svc._resolve_currency = lambda code: 1

        sale_insert = MagicMock()
        sale_insert.execute.return_value = MagicMock(data=[{"id": 100}])

        stock_select = MagicMock()
        stock_select.eq.return_value = stock_select
        stock_select.single.return_value = stock_select
        stock_select.execute.return_value = MagicMock(data={"quantity": 10})

        stock_update = MagicMock()
        stock_update.eq.return_value = stock_update
        stock_update.execute.return_value = MagicMock(data=[])

        line_insert = MagicMock()
        line_insert.execute.return_value = MagicMock(data=[{"id": 50}])

        def table_side_effect(name):
            t = MagicMock()
            if name == "sale":
                t.insert.return_value = sale_insert
            elif name == "sale_stock":
                t.insert.return_value = line_insert
            elif name == "stock":
                t.select.return_value = stock_select
                t.update.return_value = stock_update
            return t

        mock_sb.table.side_effect = table_side_effect

        svc.sync_orders()

        assert sync_log.complete.call_args.kwargs["orders_imported"] == 1
        assert sync_log.complete.call_args.kwargs["orders_skipped"] == 1


class TestResolveCustomer:
    @patch("app.services.ebay_sync.supabase")
    def test_returns_none_for_no_buyer(self, mock_sb):
        svc = _make_service()
        result = svc._resolve_customer({"buyer": {}})
        assert result is None

    @patch("app.services.ebay_sync.supabase")
    def test_finds_existing_customer(self, mock_sb):
        select_mock = MagicMock()
        select_mock.eq.return_value = select_mock
        select_mock.limit.return_value = select_mock
        select_mock.execute.return_value = MagicMock(data=[{"id": 42}])

        mock_sb.table.return_value = MagicMock(select=MagicMock(return_value=select_mock))

        svc = _make_service()
        result = svc._resolve_customer({"buyer": {"username": "existing_buyer"}})
        assert result == 42

    @patch("app.services.ebay_sync.supabase")
    def test_creates_new_customer_with_address(self, mock_sb):
        select_mock = MagicMock()
        select_mock.eq.return_value = select_mock
        select_mock.limit.return_value = select_mock
        select_mock.execute.return_value = MagicMock(data=[])

        insert_mock = MagicMock()
        insert_mock.execute.return_value = MagicMock(data=[{"id": 99}])

        table_mock = MagicMock()
        table_mock.select.return_value = select_mock
        table_mock.insert.return_value = insert_mock
        mock_sb.table.return_value = table_mock

        svc = _make_service()
        order = {
            "buyer": {"username": "new_buyer"},
            "fulfillmentStartInstructions": [
                {
                    "shippingStep": {
                        "shipTo": {
                            "contactAddress": {
                                "addressLine1": "10 Downing St",
                                "city": "London",
                                "countryCode": "GB",
                                "postalCode": "SW1A 2AA",
                            }
                        }
                    }
                }
            ],
        }
        result = svc._resolve_customer(order)

        assert result == 99
        insert_call = table_mock.insert.call_args[0][0]
        assert insert_call["name"] == "new_buyer"
        assert "source" not in insert_call
        assert insert_call["city"] == "London"


class TestResolveItem:
    @patch("app.services.ebay_sync.supabase")
    def test_returns_none_for_empty_sku(self, mock_sb):
        svc = _make_service()
        assert svc._resolve_item("", "Some Title") is None

    @patch("app.services.ebay_sync.supabase")
    def test_finds_existing_item(self, mock_sb):
        select_mock = MagicMock()
        select_mock.eq.return_value = select_mock
        select_mock.limit.return_value = select_mock
        select_mock.execute.return_value = MagicMock(data=[{"id": 15}])
        mock_sb.table.return_value = MagicMock(select=MagicMock(return_value=select_mock))

        svc = _make_service()
        assert svc._resolve_item("EXISTING-SKU", "Title") == 15

    @patch("app.services.ebay_sync.supabase")
    def test_creates_item_without_source(self, mock_sb):
        select_mock = MagicMock()
        select_mock.eq.return_value = select_mock
        select_mock.limit.return_value = select_mock
        select_mock.execute.return_value = MagicMock(data=[])

        insert_mock = MagicMock()
        insert_mock.execute.return_value = MagicMock(data=[{"id": 77}])

        table_mock = MagicMock()
        table_mock.select.return_value = select_mock
        table_mock.insert.return_value = insert_mock
        mock_sb.table.return_value = table_mock

        svc = _make_service()
        result = svc._resolve_item("NEW-SKU", "Cool Widget")

        assert result == 77
        insert_call = table_mock.insert.call_args[0][0]
        assert insert_call["item_id"] == "NEW-SKU"
        assert insert_call["description"] == "Cool Widget"
        assert "source" not in insert_call
