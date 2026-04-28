CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- GIN trigram index on item_id (part number) for substring/prefix matching.
-- Enables O(log n) lookups for ILIKE '%query%' patterns instead of sequential scans.
CREATE INDEX IF NOT EXISTS idx_item_item_id_trgm
  ON "item" USING GIN (item_id gin_trgm_ops);

-- GIN trigram index on description for substring matching.
CREATE INDEX IF NOT EXISTS idx_item_description_trgm
  ON "item" USING GIN (description gin_trgm_ops);
