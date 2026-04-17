-- Add direct item ID references to the transfer table so we no longer
-- need to join through the stock table to know which items were transferred.
ALTER TABLE "transfer"
  ADD COLUMN IF NOT EXISTS "from_item_id" integer REFERENCES "item"("id"),
  ADD COLUMN IF NOT EXISTS "to_item_id"   integer REFERENCES "item"("id");

-- Backfill from existing stock rows
UPDATE "transfer" t
SET from_item_id = s.item_id
FROM "stock" s
WHERE t.stock_id_from_id = s.id
  AND t.from_item_id IS NULL;

UPDATE "transfer" t
SET to_item_id = s.item_id
FROM "stock" s
WHERE t.stock_id_to_id = s.id
  AND t.to_item_id IS NULL;
