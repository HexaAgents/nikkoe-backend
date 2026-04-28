-- Phase 6: SQL view for stock valuation, replacing Python full-table scans.
CREATE OR REPLACE VIEW v_stock_valuation AS
WITH latest_cost AS (
  SELECT DISTINCT ON (s.item_id)
    s.item_id,
    rs.unit_price
  FROM receipt_stock rs
  JOIN stock s ON s.id = rs.stock_id
  JOIN receipt r ON r.id = rs.receipt_id AND r.status = 'ACTIVE'
  ORDER BY s.item_id, r."dateTime" DESC
)
SELECT
  i.id,
  i.item_id,
  i.description,
  COALESCE(sq.total_qty, 0) AS total_quantity,
  lc.unit_price,
  ROUND((COALESCE(sq.total_qty, 0) * COALESCE(lc.unit_price, 0))::numeric, 2) AS stock_valuation
FROM item i
LEFT JOIN (
  SELECT item_id, SUM(quantity) AS total_qty FROM stock GROUP BY item_id
) sq ON sq.item_id = i.id
LEFT JOIN latest_cost lc ON lc.item_id = i.id
ORDER BY i.item_id;
