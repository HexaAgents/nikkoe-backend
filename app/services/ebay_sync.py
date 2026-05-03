from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.dependencies import supabase
from app.ebay import client as ebay_client
from app.errors import AppError
from app.repositories.ebay_token import EbaySyncLogRepository, EbayTokenRepository
from app.repositories.sale import SaleRepository

logger = logging.getLogger(__name__)

SOURCE_TAG = "EBAY_IMPORT"


class EbaySyncService:
    def __init__(
        self,
        token_repo: EbayTokenRepository | None = None,
        sync_log_repo: EbaySyncLogRepository | None = None,
        sale_repo: SaleRepository | None = None,
    ):
        self.token_repo = token_repo or EbayTokenRepository()
        self.sync_log_repo = sync_log_repo or EbaySyncLogRepository()
        self.sale_repo = sale_repo or SaleRepository()

    def sync_orders(self, date_from: str | None = None) -> dict:
        """Run a sync: fetch eBay orders and import them as Sales."""
        if date_from is None:
            last = self.sync_log_repo.get_last_successful()
            if last and last.get("sync_to"):
                date_from = last["sync_to"]

        log = self.sync_log_repo.create(sync_from=date_from)
        log_id = log["id"]

        try:
            access_token = ebay_client.get_valid_access_token(self.token_repo)
            if not access_token:
                self.sync_log_repo.fail(log_id, "No eBay token linked")
                return {"error": "No eBay token linked"}

            channel_id = self._get_ebay_channel_id()
            location_id = self._get_ebay_location_id()

            orders = ebay_client.get_all_orders(access_token, date_from=date_from)

            fetched = len(orders)
            imported = 0
            skipped = 0
            oversold_messages: list[str] = []

            for order in orders:
                if self._is_paid(order) and not self._already_imported(order):
                    sale_row = self._import_order(order, channel_id, location_id, oversold_messages)
                    if sale_row is None:
                        skipped += 1
                    else:
                        imported += 1
                else:
                    skipped += 1

            sync_to = datetime.now(timezone.utc).isoformat()
            error_message = "; ".join(oversold_messages) if oversold_messages else None
            if error_message:
                logger.warning("eBay sync completed with %d oversold order(s): %s", len(oversold_messages), error_message)

            result = self.sync_log_repo.complete(
                log_id,
                orders_fetched=fetched,
                orders_imported=imported,
                orders_skipped=skipped,
                sync_to=sync_to,
            )
            if error_message:
                # Surface oversold orders to the caller without marking the whole sync as FAILED.
                # The status stays SUCCESS but error_message is populated for visibility.
                supabase.table(EbaySyncLogRepository.TABLE).update({"error_message": error_message}).eq(
                    "id", log_id
                ).execute()
                result["error_message"] = error_message
            return result

        except Exception as exc:
            logger.exception("eBay sync failed")
            self.sync_log_repo.fail(log_id, str(exc))
            return {"error": str(exc)}

    def _is_paid(self, order: dict) -> bool:
        status = order.get("orderPaymentStatus", "")
        return status in ("PAID", "PARTIALLY_REFUNDED", "FULLY_REFUNDED")

    def _already_imported(self, order: dict) -> bool:
        order_id = order.get("orderId", "")
        if not order_id:
            return True
        resp = supabase.table("sale").select("id").eq("channel_ref", order_id).limit(1).execute()
        return bool(resp.data)

    def _import_order(
        self,
        order: dict,
        channel_id: int | None = None,
        location_id: int | None = None,
        oversold_messages: list[str] | None = None,
    ) -> dict | None:
        """Import a single eBay order as a Sale via SaleRepository.create.

        Returns the inserted sale row on success, or None if the order was skipped
        because it would have driven a stock row negative (oversell). In the
        oversell case, a human-readable note is appended to oversold_messages.
        """
        order_id = order["orderId"]
        creation_date = order.get("creationDate", datetime.now(timezone.utc).isoformat())

        if channel_id is None:
            channel_id = self._get_ebay_channel_id()
        if location_id is None:
            location_id = self._get_ebay_location_id()
        customer_id = self._resolve_customer(order)

        sale_data: dict = {
            "channel_id": channel_id,
            "channel_ref": order_id,
            "date": creation_date,
            "source": SOURCE_TAG,
        }
        if customer_id:
            sale_data["customer_id"] = customer_id

        lines_data: list[dict] = []
        for line_item in order.get("lineItems", []):
            mapped = self._map_line_item(line_item, location_id)
            item_db_id = mapped.pop("_item_db_id", None)
            if not item_db_id:
                # Without a resolved item we cannot record the line; skip this line.
                continue
            line = {
                "item_id": item_db_id,
                "location_id": location_id,
                "quantity": mapped.get("quantity"),
                "unit_price": mapped.get("unit_price"),
            }
            if "currency_id" in mapped:
                line["currency_id"] = mapped["currency_id"]
            lines_data.append(line)

        if not lines_data:
            return None

        try:
            return self.sale_repo.create(sale_data, lines_data)
        except AppError as exc:
            if exc.status_code == 400 and "Insufficient stock" in exc.message:
                msg = f"order {order_id}: {exc.message}"
                logger.warning("Skipping eBay %s", msg)
                if oversold_messages is not None:
                    oversold_messages.append(msg)
                return None
            raise

    def _map_line_item(self, line_item: dict, location_id: int) -> dict:
        sku = line_item.get("sku") or line_item.get("legacyItemId", "")
        title = line_item.get("title", "")
        quantity = line_item.get("quantity", 1)

        total_info = line_item.get("total", {})
        unit_price = float(total_info.get("value", "0"))
        currency_code = total_info.get("currency", "USD")

        if quantity and quantity > 0:
            unit_price = unit_price / quantity

        item_db_id = self._resolve_item(sku, title)
        currency_id = self._resolve_currency(currency_code)

        result: dict = {
            "quantity": max(quantity, 1),
            "unit_price": unit_price,
            "_item_db_id": item_db_id,
        }
        if currency_id:
            result["currency_id"] = currency_id
        return result

    def _resolve_item(self, sku: str, title: str) -> int | None:
        if not sku:
            return None

        resp = supabase.table("item").select("id").eq("item_id", sku).limit(1).execute()
        if resp.data:
            return resp.data[0]["id"]

        new_item = (
            supabase.table("item")
            .insert(
                {
                    "item_id": sku,
                    "description": title[:1000] if title else None,
                }
            )
            .execute()
        )
        return new_item.data[0]["id"]

    def _resolve_stock(self, item_id: int | None, location_id: int) -> int | None:
        if not item_id:
            return None

        resp = (
            supabase.table("stock")
            .select("id")
            .eq("item_id", item_id)
            .eq("location_id", location_id)
            .limit(1)
            .execute()
        )
        if resp.data:
            return resp.data[0]["id"]

        new_stock = (
            supabase.table("stock")
            .insert(
                {
                    "item_id": item_id,
                    "location_id": location_id,
                    "quantity": 0,
                }
            )
            .execute()
        )
        return new_stock.data[0]["id"]

    def _resolve_customer(self, order: dict) -> int | None:
        buyer = order.get("buyer", {})
        username = buyer.get("username", "")
        if not username:
            return None

        resp = supabase.table("customer").select("id").eq("name", username).limit(1).execute()
        if resp.data:
            return resp.data[0]["id"]

        shipping = order.get("fulfillmentStartInstructions", [{}])
        address = {}
        if shipping:
            ship_to = shipping[0].get("shippingStep", {}).get("shipTo", {})
            contact = ship_to.get("contactAddress", {})
            address = {
                "address_line1": contact.get("addressLine1"),
                "address_line2": contact.get("addressLine2"),
                "city": contact.get("city"),
                "country": contact.get("countryCode"),
                "postal_code": contact.get("postalCode"),
            }

        customer_data = {
            "name": username,
            **{k: v for k, v in address.items() if v},
        }
        new_customer = supabase.table("customer").insert(customer_data).execute()
        return new_customer.data[0]["id"]

    def _resolve_currency(self, code: str) -> int | None:
        if not code:
            return None
        resp = supabase.table("currency").select("id").eq("name", code).limit(1).execute()
        if resp.data:
            return resp.data[0]["id"]
        return None

    def _get_ebay_channel_id(self) -> int | None:
        resp = supabase.table("channel").select("id").eq("name", "eBay").limit(1).execute()
        if resp.data:
            return resp.data[0]["id"]
        return None

    def _get_ebay_location_id(self) -> int:
        resp = supabase.table("location").select("id").eq("code", "EBAY").limit(1).execute()
        if resp.data:
            return resp.data[0]["id"]
        new_loc = supabase.table("location").insert({"code": "EBAY"}).execute()
        return new_loc.data[0]["id"]
