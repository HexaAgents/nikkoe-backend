CREATE OR REPLACE FUNCTION search_sales_by_part_number(search_term text, lim int DEFAULT 500)
RETURNS SETOF bigint AS $$
  SELECT sub.id FROM (
    SELECT DISTINCT s.id, s.date
    FROM sale s
    JOIN sale_stock ss ON ss.sale_id = s.id
    JOIN stock st ON st.id = ss.stock_id
    JOIN item i ON i.id = st.item_id
    WHERE i.item_id ILIKE '%' || search_term || '%'
  ) sub
  ORDER BY sub.date DESC
  LIMIT lim;
$$ LANGUAGE sql STABLE;
