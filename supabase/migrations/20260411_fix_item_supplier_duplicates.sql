-- Remove duplicate (item_id, supplier_id) rows, keeping only the most recent
-- entry per pair (by date_time, then by highest id as tiebreaker).
DELETE FROM item_supplier
WHERE id NOT IN (
    SELECT DISTINCT ON (item_id, supplier_id) id
    FROM item_supplier
    ORDER BY item_id, supplier_id, date_time DESC NULLS LAST, id DESC
);

-- Prevent future duplicates
ALTER TABLE item_supplier
ADD CONSTRAINT uq_item_supplier UNIQUE (item_id, supplier_id);
