-- Phase 3b: RPC for category stats to replace full-table scan in Python.
CREATE OR REPLACE FUNCTION get_category_stats()
RETURNS TABLE(category_id bigint, item_count bigint, total_quantity bigint)
LANGUAGE sql STABLE AS $$
  SELECT i.category_id, COUNT(DISTINCT i.id), COALESCE(SUM(s.quantity), 0)
  FROM item i
  LEFT JOIN stock s ON s.item_id = i.id
  WHERE i.category_id IS NOT NULL
  GROUP BY i.category_id;
$$;
