-- Phase 1: Add missing constraints and indexes for data integrity and query performance.

-- 1a. Unique constraint on stock(item_id, location_id).
-- Deduplicate first: merge quantities into the row with the lowest id per (item_id, location_id).
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'uq_stock_item_location'
  ) THEN
    -- Build a mapping from duplicate stock ids to the keeper id for each (item_id, location_id) pair.
    CREATE TEMP TABLE _stock_dedup AS
    SELECT s.id AS old_id, d.keep_id
    FROM stock s
    JOIN (
      SELECT item_id, location_id, MIN(id) AS keep_id
      FROM stock GROUP BY item_id, location_id HAVING COUNT(*) > 1
    ) d ON s.item_id = d.item_id AND s.location_id = d.location_id AND s.id != d.keep_id;

    -- Merge duplicate quantities into the keeper row.
    UPDATE stock s
    SET quantity = s.quantity + agg.extra_qty
    FROM (
      SELECT d.keep_id, SUM(s2.quantity) AS extra_qty
      FROM _stock_dedup d JOIN stock s2 ON s2.id = d.old_id
      GROUP BY d.keep_id
    ) agg
    WHERE s.id = agg.keep_id;

    -- Re-point all FK references from duplicates to the keeper.
    UPDATE sale_stock SET stock_id = d.keep_id FROM _stock_dedup d WHERE sale_stock.stock_id = d.old_id;
    UPDATE receipt_stock SET stock_id = d.keep_id FROM _stock_dedup d WHERE receipt_stock.stock_id = d.old_id;
    UPDATE transfer SET stock_id_from_id = d.keep_id FROM _stock_dedup d WHERE transfer.stock_id_from_id = d.old_id;
    UPDATE transfer SET stock_id_to_id = d.keep_id FROM _stock_dedup d WHERE transfer.stock_id_to_id = d.old_id;

    -- Now safe to delete the duplicate rows.
    DELETE FROM stock WHERE id IN (SELECT old_id FROM _stock_dedup);

    DROP TABLE _stock_dedup;

    ALTER TABLE stock ADD CONSTRAINT uq_stock_item_location UNIQUE (item_id, location_id);
  END IF;
END $$;

-- 1b. Missing indexes on transfer table.
CREATE INDEX IF NOT EXISTS idx_transfer_stock_from ON transfer(stock_id_from_id);
CREATE INDEX IF NOT EXISTS idx_transfer_stock_to   ON transfer(stock_id_to_id);
CREATE INDEX IF NOT EXISTS idx_transfer_date_desc  ON transfer(date DESC);
CREATE INDEX IF NOT EXISTS idx_transfer_from_item  ON transfer(from_item_id);
CREATE INDEX IF NOT EXISTS idx_transfer_to_item    ON transfer(to_item_id);

-- 1c. Index on item(search_id) for equality lookups.
CREATE INDEX IF NOT EXISTS idx_item_search_id ON item(search_id);

-- 1d. CHECK constraints on status columns.
DO $$ BEGIN
  ALTER TABLE sale ADD CONSTRAINT chk_sale_status CHECK (status IN ('ACTIVE', 'VOIDED'));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  ALTER TABLE receipt ADD CONSTRAINT chk_receipt_status CHECK (status IN ('ACTIVE', 'VOIDED'));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- 1e. Trigram indexes on customer(name) and supplier(name) for ILIKE searches.
CREATE INDEX IF NOT EXISTS idx_customer_name_trgm ON customer USING GIN (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_supplier_name_trgm ON supplier USING GIN (name gin_trgm_ops);
