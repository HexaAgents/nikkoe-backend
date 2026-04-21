-- Phase 4: Clean up dead code and rename confusing FK columns.

-- 4a. Drop the dead UUID-based RPCs that target non-existent tables.
DROP FUNCTION IF EXISTS create_receipt(jsonb, jsonb);
DROP FUNCTION IF EXISTS create_sale(jsonb, jsonb);

-- 4d. Rename confusing double-_id FK columns on sale.
ALTER TABLE sale RENAME COLUMN customer_id_id TO customer_id;
ALTER TABLE sale RENAME COLUMN channel_id_id TO channel_id;
