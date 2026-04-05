# fix_prices

One-shot script to fix `Sale_Stock` rows that have `unit_price = 0` in Supabase by scraping the correct prices from the source website.

## How it works

1. Queries Supabase for every `Sale_Stock` row where `unit_price = 0`.
2. For each row, resolves the **sale date**, **customer name**, and **part number** (item_id).
3. Uses Selenium to navigate the source website and locate the matching sale by those three fields.
4. Updates the `unit_price` in Supabase with the value found on the website.

## Setup

```bash
cd scripts/fix_prices
cp .env.example .env          # fill in your real credentials
pip install -r requirements.txt
```

You also need **Google Chrome** installed. Selenium 4+ auto-manages the ChromeDriver.

## Customisation required

Before running you **must** edit the TODO sections in `fix_prices.py`:

- **`login()`** — update the CSS selectors to match your website's login form (or delete the function if no login is needed).
- **`scrape_price()`** — update navigation and table selectors to match how sales appear on the website.
- **`_dates_match()`** — adjust the date format string to match how dates are displayed on the website.
- **`scrape_price_with_pagination()`** — uncomment and adapt the pagination loop if the website spans multiple pages.

## Usage

```bash
# Preview what would change (no DB writes)
python fix_prices.py --dry-run

# Run for real
python fix_prices.py
```

## Features

- **Resumable** — progress is saved to `progress.json`; re-running skips already-processed rows.
- **Dry-run mode** — shows what would be updated without touching the database.
- **Logging** — all actions are logged to both the console and `fix_prices.log`.
- **Error screenshots** — on Selenium failures, a screenshot is saved as `error_<id>.png` for debugging.
