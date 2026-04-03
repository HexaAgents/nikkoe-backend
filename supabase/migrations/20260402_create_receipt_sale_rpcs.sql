-- Atomic receipt creation: inserts header + lines in a single transaction
CREATE OR REPLACE FUNCTION create_receipt(
  p_receipt jsonb,
  p_lines jsonb
) RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
  v_receipt_id uuid;
  v_result jsonb;
  v_line jsonb;
BEGIN
  INSERT INTO receipts (supplier_id, reference, note)
  VALUES (
    (p_receipt->>'supplier_id')::uuid,
    p_receipt->>'reference',
    p_receipt->>'note'
  )
  RETURNING receipt_id INTO v_receipt_id;

  FOR v_line IN SELECT * FROM jsonb_array_elements(p_lines)
  LOOP
    INSERT INTO receipt_lines (receipt_line_id, receipt_id, item_id, location_id, quantity, unit_cost, currency_code)
    VALUES (
      gen_random_uuid(),
      v_receipt_id,
      (v_line->>'item_id')::uuid,
      (v_line->>'location_id')::uuid,
      (v_line->>'quantity')::int,
      (v_line->>'unit_cost')::numeric,
      v_line->>'currency_code'
    );
  END LOOP;

  SELECT to_jsonb(r.*) INTO v_result FROM receipts r WHERE r.receipt_id = v_receipt_id;
  RETURN v_result;
END;
$$;

-- Atomic sale creation: inserts header + lines in a single transaction
CREATE OR REPLACE FUNCTION create_sale(
  p_sale jsonb,
  p_lines jsonb
) RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
  v_sale_id uuid;
  v_result jsonb;
  v_line jsonb;
BEGIN
  INSERT INTO sales (sale_id, customer_name, channel_id, note)
  VALUES (
    gen_random_uuid(),
    p_sale->>'customer_name',
    (p_sale->>'channel_id')::uuid,
    p_sale->>'note'
  )
  RETURNING sale_id INTO v_sale_id;

  FOR v_line IN SELECT * FROM jsonb_array_elements(p_lines)
  LOOP
    INSERT INTO sale_lines (sale_line_id, sale_id, item_id, location_id, quantity, unit_price, currency_code)
    VALUES (
      gen_random_uuid(),
      v_sale_id,
      (v_line->>'item_id')::uuid,
      (v_line->>'location_id')::uuid,
      (v_line->>'quantity')::int,
      (v_line->>'unit_price')::numeric,
      v_line->>'currency_code'
    );
  END LOOP;

  SELECT to_jsonb(s.*) INTO v_result FROM sales s WHERE s.sale_id = v_sale_id;
  RETURN v_result;
END;
$$;
