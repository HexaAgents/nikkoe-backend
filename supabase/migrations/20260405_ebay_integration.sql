-- Add source column to existing tables for eBay import tracking
ALTER TABLE "Sale"       ADD COLUMN IF NOT EXISTS source text;
ALTER TABLE "Sale_Stock" ADD COLUMN IF NOT EXISTS source text;
ALTER TABLE "Item"       ADD COLUMN IF NOT EXISTS source text;
ALTER TABLE "Customer"   ADD COLUMN IF NOT EXISTS source text;
ALTER TABLE "Stock"      ADD COLUMN IF NOT EXISTS source text;

CREATE INDEX IF NOT EXISTS idx_sale_source       ON "Sale"(source)       WHERE source IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_sale_stock_source  ON "Sale_Stock"(source) WHERE source IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_item_source       ON "Item"(source)       WHERE source IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_customer_source   ON "Customer"(source)   WHERE source IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_stock_source      ON "Stock"(source)      WHERE source IS NOT NULL;

-- Store eBay OAuth tokens
CREATE TABLE IF NOT EXISTS "Ebay_Token" (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ebay_user_id text,
    access_token text NOT NULL,
    refresh_token text NOT NULL,
    token_expiry timestamptz NOT NULL,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- Track sync runs
CREATE TABLE IF NOT EXISTS "Ebay_Sync_Log" (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    started_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    status text NOT NULL DEFAULT 'RUNNING',
    orders_fetched int DEFAULT 0,
    orders_imported int DEFAULT 0,
    orders_skipped int DEFAULT 0,
    error_message text,
    sync_from timestamptz,
    sync_to timestamptz
);

-- Seed eBay channel and location
INSERT INTO "Channel" (name) VALUES ('eBay') ON CONFLICT DO NOTHING;
INSERT INTO "Location" (code) VALUES ('EBAY') ON CONFLICT DO NOTHING;
