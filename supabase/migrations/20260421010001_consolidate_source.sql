-- Phase 5: Consolidate source tracking.
-- Keep source only on sale (header-level provenance). Drop from line/item/stock/customer tables.

-- Drop partial indexes first (they reference the columns being dropped).
DROP INDEX IF EXISTS idx_sale_stock_source;
DROP INDEX IF EXISTS idx_item_source;
DROP INDEX IF EXISTS idx_customer_source;
DROP INDEX IF EXISTS idx_stock_source;

-- Drop the source columns from non-sale tables (lowercase -- the actual table names).
ALTER TABLE sale_stock DROP COLUMN IF EXISTS source;
ALTER TABLE item DROP COLUMN IF EXISTS source;
ALTER TABLE customer DROP COLUMN IF EXISTS source;
ALTER TABLE stock DROP COLUMN IF EXISTS source;
