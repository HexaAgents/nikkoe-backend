"""
fix_prices.py
─────────────
Finds Sale_Stock rows in Supabase where unit_price is 0, scrapes the correct
price from the source website, and updates the database.

Matching logic: a website sale matches a DB sale when the date/time, customer
name, and part number (item_id) all agree.

Usage:
    python fix_prices.py                # live run – writes to DB
    python fix_prices.py --dry-run      # preview only – no DB writes
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from supabase import Client, create_client

# ── configuration ────────────────────────────────────────────────────────────

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
WEBSITE_URL = os.environ.get("WEBSITE_URL", "")
WEBSITE_USERNAME = os.environ.get("WEBSITE_USERNAME", "")
WEBSITE_PASSWORD = os.environ.get("WEBSITE_PASSWORD", "")

WAIT_TIMEOUT = 15          # seconds to wait for page elements
PAGE_DELAY = 1.0           # polite delay between page loads
PROGRESS_FILE = Path(__file__).parent / "progress.json"

# ── logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(Path(__file__).parent / "fix_prices.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("fix_prices")

# ── Supabase client ─────────────────────────────────────────────────────────

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ── helpers ──────────────────────────────────────────────────────────────────


def load_progress() -> set[int]:
    """Return set of Sale_Stock IDs already processed (survives restarts)."""
    if PROGRESS_FILE.exists():
        return set(json.loads(PROGRESS_FILE.read_text()))
    return set()


def save_progress(done_ids: set[int]) -> None:
    PROGRESS_FILE.write_text(json.dumps(sorted(done_ids)))


# ── database queries ─────────────────────────────────────────────────────────


def get_zero_price_lines() -> list[dict]:
    """
    Fetch every Sale_Stock row where unit_price = 0, together with the
    sale date, customer name, and item part number needed for matching.
    """
    resp = (
        supabase.table("Sale_Stock")
        .select("*")
        .eq("unit_price", 0)
        .execute()
    )
    lines = resp.data or []
    if not lines:
        return []

    sale_ids = list({ln["sale_id"] for ln in lines})
    stock_ids = list({ln["stock_id"] for ln in lines if ln.get("stock_id")})

    sales_map: dict[int, dict] = {}
    for sid in sale_ids:
        sale_resp = supabase.table("Sale").select("*").eq("id", sid).maybe_single().execute()
        if sale_resp.data:
            sale = sale_resp.data
            if sale.get("customer_id_id"):
                cust = (
                    supabase.table("Customer")
                    .select("id, name")
                    .eq("id", sale["customer_id_id"])
                    .maybe_single()
                    .execute()
                )
                sale["_customer_name"] = cust.data["name"] if cust.data else None
            else:
                sale["_customer_name"] = None
            sales_map[sid] = sale

    stocks_map: dict[int, dict] = {}
    for stk_id in stock_ids:
        stk_resp = supabase.table("Stock").select("*").eq("id", stk_id).maybe_single().execute()
        if stk_resp.data:
            item_resp = (
                supabase.table("Item")
                .select("id, item_id")
                .eq("id", stk_resp.data.get("item_id"))
                .maybe_single()
                .execute()
            )
            stk_resp.data["_item_code"] = item_resp.data["item_id"] if item_resp.data else None
            stocks_map[stk_id] = stk_resp.data

    enriched: list[dict] = []
    for ln in lines:
        sale = sales_map.get(ln["sale_id"])
        stock = stocks_map.get(ln.get("stock_id"))
        ln["_sale_date"] = sale.get("date") if sale else None
        ln["_customer_name"] = sale.get("_customer_name") if sale else None
        ln["_item_code"] = stock.get("_item_code") if stock else None
        enriched.append(ln)

    return enriched


def update_unit_price(sale_stock_id: int, correct_price: float) -> None:
    supabase.table("Sale_Stock").update(
        {"unit_price": correct_price}
    ).eq("id", sale_stock_id).execute()


# ── Selenium helpers ─────────────────────────────────────────────────────────


def create_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(options=options)


def login(driver: webdriver.Chrome) -> None:
    """
    Log in to the website. Adapt the selectors below to match the real
    login page.  Delete this function if no authentication is required.

    ┌──────────────────────────────────────────────────────────────────┐
    │  TODO: update selectors to match your website's login form.     │
    └──────────────────────────────────────────────────────────────────┘
    """
    driver.get(f"{WEBSITE_URL}/login")
    wait = WebDriverWait(driver, WAIT_TIMEOUT)

    # --- adapt these selectors ------------------------------------------------
    username_field = wait.until(EC.presence_of_element_located((By.ID, "username")))
    password_field = driver.find_element(By.ID, "password")
    submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    # --------------------------------------------------------------------------

    username_field.clear()
    username_field.send_keys(WEBSITE_USERNAME)
    password_field.clear()
    password_field.send_keys(WEBSITE_PASSWORD)
    submit_btn.click()

    wait.until(EC.url_changes(f"{WEBSITE_URL}/login"))
    log.info("Logged in to %s", WEBSITE_URL)


def scrape_price(
    driver: webdriver.Chrome,
    sale_date: str,
    customer_name: str,
    item_code: str,
) -> float | None:
    """
    Navigate the website and find the unit price for a sale that matches
    the given date/time, customer, and part number.

    ┌──────────────────────────────────────────────────────────────────┐
    │  TODO: replace the placeholder logic below with real selectors  │
    │  and navigation that match your source website.                 │
    │                                                                 │
    │  The three pieces of data used for matching are:                │
    │    • sale_date    – e.g. "2026-03-15T14:30:00+00:00"           │
    │    • customer_name – e.g. "Acme Corp"                          │
    │    • item_code    – the part number, e.g. "WIDGET-001"         │
    │                                                                 │
    │  Return the correct unit price as a float, or None if the      │
    │  sale could not be found on the website.                        │
    └──────────────────────────────────────────────────────────────────┘
    """
    wait = WebDriverWait(driver, WAIT_TIMEOUT)

    # ── STEP 1: navigate to the sales list / search page ─────────────────────
    #
    # Option A – if the site has a search / filter page:
    #   driver.get(f"{WEBSITE_URL}/sales")
    #   search_box = wait.until(EC.presence_of_element_located((By.ID, "search")))
    #   search_box.send_keys(customer_name)
    #   driver.find_element(By.CSS_SELECTOR, "button.search-btn").click()
    #
    # Option B – if each sale has a direct URL you can construct:
    #   driver.get(f"{WEBSITE_URL}/sales?date={sale_date}&customer={customer_name}")

    driver.get(f"{WEBSITE_URL}/sales")
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table")))

    # ── STEP 2: iterate through rows and find the matching sale ──────────────
    #
    # Adapt the selector and column indices to your website's table layout.
    #
    # Example assumes a table with columns:
    #   [0] Date  |  [1] Customer  |  [2] Part  |  [3] Qty  |  [4] Unit Price

    rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
    for row in rows:
        cells = row.find_elements(By.TAG_NAME, "td")
        if len(cells) < 5:
            continue

        row_date = cells[0].text.strip()
        row_customer = cells[1].text.strip()
        row_part = cells[2].text.strip()
        row_price_text = cells[4].text.strip()

        if not _dates_match(row_date, sale_date):
            continue
        if row_customer.lower() != customer_name.lower():
            continue
        if row_part.lower() != item_code.lower():
            continue

        try:
            price = float(row_price_text.replace(",", "").replace("$", ""))
            return price
        except ValueError:
            log.warning("Could not parse price '%s'", row_price_text)
            return None

    return None


def _dates_match(website_date_str: str, db_date_str: str) -> bool:
    """
    Compare a date string from the website with one from the database.

    ┌──────────────────────────────────────────────────────────────────┐
    │  TODO: adjust the website format string to match how dates      │
    │  appear on your website (e.g. "15/03/2026 14:30",              │
    │  "Mar 15, 2026 2:30 PM", etc.)                                 │
    └──────────────────────────────────────────────────────────────────┘
    """
    try:
        db_dt = datetime.fromisoformat(db_date_str)
    except (ValueError, TypeError):
        return False

    website_formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%m/%d/%Y %H:%M",
        "%d %b %Y %H:%M",
        "%b %d, %Y %I:%M %p",
    ]
    for fmt in website_formats:
        try:
            web_dt = datetime.strptime(website_date_str, fmt)
            if db_dt.replace(tzinfo=None) == web_dt:
                return True
        except ValueError:
            continue

    return False


# ── pagination helper ────────────────────────────────────────────────────────

def scrape_price_with_pagination(
    driver: webdriver.Chrome,
    sale_date: str,
    customer_name: str,
    item_code: str,
) -> float | None:
    """
    Wraps scrape_price with pagination support.

    ┌──────────────────────────────────────────────────────────────────┐
    │  TODO: if the website paginates results, implement clicking     │
    │  through pages here.  If everything is on one page, this just   │
    │  delegates to scrape_price.                                     │
    └──────────────────────────────────────────────────────────────────┘
    """
    price = scrape_price(driver, sale_date, customer_name, item_code)
    if price is not None:
        return price

    # Example pagination – uncomment and adapt if the site has a "Next" button:
    #
    # while True:
    #     try:
    #         next_btn = driver.find_element(By.CSS_SELECTOR, "button.next-page")
    #         if not next_btn.is_enabled():
    #             break
    #         next_btn.click()
    #         time.sleep(PAGE_DELAY)
    #         price = scrape_price(driver, sale_date, customer_name, item_code)
    #         if price is not None:
    #             return price
    #     except Exception:
    #         break

    return None


# ── main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Fix zero-price sale lines from website data")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be updated without writing to the database",
    )
    args = parser.parse_args()

    log.info("Starting fix_prices  (dry_run=%s)", args.dry_run)

    lines = get_zero_price_lines()
    log.info("Found %d Sale_Stock rows with unit_price = 0", len(lines))
    if not lines:
        log.info("Nothing to fix – exiting")
        return

    done_ids = load_progress()
    remaining = [ln for ln in lines if ln["id"] not in done_ids]
    if done_ids:
        log.info("Resuming – %d already processed, %d remaining", len(done_ids), len(remaining))

    driver = create_driver()
    updated = 0
    skipped = 0

    try:
        if WEBSITE_USERNAME:
            login(driver)

        for i, line in enumerate(remaining, 1):
            line_id = line["id"]
            sale_date = line.get("_sale_date")
            customer = line.get("_customer_name")
            item_code = line.get("_item_code")

            log.info(
                "[%d/%d]  Sale_Stock id=%d  date=%s  customer=%s  part=%s",
                i, len(remaining), line_id, sale_date, customer, item_code,
            )

            if not all([sale_date, customer, item_code]):
                log.warning("  ↳ Skipping – missing matching data (date/customer/part)")
                skipped += 1
                done_ids.add(line_id)
                save_progress(done_ids)
                continue

            try:
                price = scrape_price_with_pagination(driver, sale_date, customer, item_code)
            except Exception as exc:
                log.error("  ↳ Selenium error: %s", exc)
                driver.save_screenshot(
                    str(Path(__file__).parent / f"error_{line_id}.png")
                )
                skipped += 1
                continue

            if price is None:
                log.warning("  ↳ No matching sale found on website")
                skipped += 1
            elif price <= 0:
                log.warning("  ↳ Website price is %s – skipping", price)
                skipped += 1
            else:
                if args.dry_run:
                    log.info("  ↳ [DRY RUN] Would update unit_price → %.2f", price)
                else:
                    update_unit_price(line_id, price)
                    log.info("  ↳ Updated unit_price → %.2f", price)
                updated += 1

            done_ids.add(line_id)
            save_progress(done_ids)
            time.sleep(PAGE_DELAY)

    except KeyboardInterrupt:
        log.info("Interrupted – progress saved (%d processed so far)", len(done_ids))
    finally:
        driver.quit()

    log.info("Done.  updated=%d  skipped=%d  total=%d", updated, skipped, len(remaining))


if __name__ == "__main__":
    main()
