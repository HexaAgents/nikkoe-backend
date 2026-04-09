CREATE INDEX IF NOT EXISTS idx_stock_item_id ON stock(item_id);
CREATE INDEX IF NOT EXISTS idx_receipt_stock_stock_id ON receipt_stock(stock_id);
CREATE INDEX IF NOT EXISTS idx_receipt_stock_receipt_id ON receipt_stock(receipt_id);
CREATE INDEX IF NOT EXISTS idx_sale_stock_stock_id ON sale_stock(stock_id);
CREATE INDEX IF NOT EXISTS idx_sale_stock_sale_id ON sale_stock(sale_id);
CREATE INDEX IF NOT EXISTS idx_receipt_status ON receipt(status);
CREATE INDEX IF NOT EXISTS idx_sale_status ON sale(status);

CREATE OR REPLACE FUNCTION get_items_sorted(
  p_sort_by text DEFAULT 'item_id',
  p_limit int DEFAULT 20,
  p_offset int DEFAULT 0,
  p_search text DEFAULT NULL
)
RETURNS TABLE(
  id bigint,
  item_id text,
  description text,
  category_id bigint,
  search_id text,
  sort_value text,
  total_count bigint
)
LANGUAGE plpgsql STABLE
AS $$
BEGIN
  IF p_sort_by = 'latest_receipt' THEN
    RETURN QUERY
      WITH lr AS (
        SELECT s.item_id AS iid, MAX(r."dateTime") AS val
        FROM receipt_stock rs
        JOIN stock s  ON s.id  = rs.stock_id
        JOIN receipt r ON r.id = rs.receipt_id AND r.status = 'ACTIVE'
        GROUP BY s.item_id
      )
      SELECT i.id, i.item_id, i.description, i.category_id, i.search_id,
             lr.val::text AS sort_value,
             COUNT(*) OVER() AS total_count
      FROM item i
      LEFT JOIN lr ON lr.iid = i.id
      WHERE (p_search IS NULL OR i.item_id ILIKE '%' || p_search || '%')
      ORDER BY lr.val DESC NULLS LAST, i.item_id ASC
      LIMIT p_limit OFFSET p_offset;

  ELSIF p_sort_by = 'latest_sale' THEN
    RETURN QUERY
      WITH ls AS (
        SELECT s.item_id AS iid, MAX(sa.date) AS val
        FROM sale_stock ss
        JOIN stock s  ON s.id  = ss.stock_id
        JOIN sale  sa ON sa.id = ss.sale_id AND sa.status = 'ACTIVE'
        GROUP BY s.item_id
      )
      SELECT i.id, i.item_id, i.description, i.category_id, i.search_id,
             ls.val::text AS sort_value,
             COUNT(*) OVER() AS total_count
      FROM item i
      LEFT JOIN ls ON ls.iid = i.id
      WHERE (p_search IS NULL OR i.item_id ILIKE '%' || p_search || '%')
      ORDER BY ls.val DESC NULLS LAST, i.item_id ASC
      LIMIT p_limit OFFSET p_offset;

  ELSIF p_sort_by = 'total_quantity' THEN
    RETURN QUERY
      WITH q AS (
        SELECT s.item_id AS iid, SUM(s.quantity) AS val
        FROM stock s
        GROUP BY s.item_id
      )
      SELECT i.id, i.item_id, i.description, i.category_id, i.search_id,
             COALESCE(q.val, 0)::text AS sort_value,
             COUNT(*) OVER() AS total_count
      FROM item i
      LEFT JOIN q ON q.iid = i.id
      WHERE (p_search IS NULL OR i.item_id ILIKE '%' || p_search || '%')
      ORDER BY COALESCE(q.val, 0) DESC, i.item_id ASC
      LIMIT p_limit OFFSET p_offset;

  ELSE
    RETURN QUERY
      SELECT i.id, i.item_id, i.description, i.category_id, i.search_id,
             i.item_id AS sort_value,
             COUNT(*) OVER() AS total_count
      FROM item i
      WHERE (p_search IS NULL OR i.item_id ILIKE '%' || p_search || '%')
      ORDER BY i.item_id ASC
      LIMIT p_limit OFFSET p_offset;
  END IF;
END;
$$;
