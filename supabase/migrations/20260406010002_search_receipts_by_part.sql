CREATE OR REPLACE FUNCTION search_receipts_by_part_number(search_term text, lim int DEFAULT 500)
RETURNS SETOF bigint AS $$
  SELECT sub.id FROM (
    SELECT DISTINCT r.id, r."dateTime"
    FROM receipt r
    JOIN receipt_stock rs ON rs.receipt_id = r.id
    JOIN stock st ON st.id = rs.stock_id
    JOIN item i ON i.id = st.item_id
    WHERE i.item_id ILIKE '%' || search_term || '%'
  ) sub
  ORDER BY sub."dateTime" DESC
  LIMIT lim;
$$ LANGUAGE sql STABLE;
