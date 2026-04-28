-- Phase 2: Transactional RPCs for atomic sale/receipt create and void operations.
-- Replaces multi-round-trip Python logic with single-call Postgres functions.

-- 2a. Atomic sale creation.
CREATE OR REPLACE FUNCTION create_sale_tx(p_sale jsonb, p_lines jsonb)
RETURNS bigint LANGUAGE plpgsql AS $$
DECLARE
  v_sale_id bigint;
  v_line jsonb;
  v_stock_id bigint;
BEGIN
  INSERT INTO sale (date, customer_id, channel_id, channel_ref, note, user_id, source)
  VALUES (
    COALESCE((p_sale->>'date')::timestamptz, now()),
    (p_sale->>'customer_id')::bigint,
    (p_sale->>'channel_id')::bigint,
    p_sale->>'channel_ref',
    p_sale->>'note',
    (p_sale->>'user_id')::bigint,
    p_sale->>'source'
  )
  RETURNING id INTO v_sale_id;

  FOR v_line IN SELECT * FROM jsonb_array_elements(p_lines) LOOP
    INSERT INTO stock (item_id, location_id, quantity)
    VALUES ((v_line->>'item_id')::bigint, (v_line->>'location_id')::bigint, 0)
    ON CONFLICT (item_id, location_id) DO NOTHING;

    SELECT id INTO v_stock_id FROM stock
    WHERE item_id = (v_line->>'item_id')::bigint
      AND location_id = (v_line->>'location_id')::bigint;

    INSERT INTO sale_stock (sale_id, stock_id, quantity, unit_price, currency_id)
    VALUES (v_sale_id, v_stock_id,
            (v_line->>'quantity')::int, (v_line->>'unit_price')::numeric,
            (v_line->>'currency_id')::bigint);

    UPDATE stock SET quantity = quantity - (v_line->>'quantity')::int WHERE id = v_stock_id;
  END LOOP;

  RETURN v_sale_id;
END; $$;

-- 2b. Atomic receipt creation.
CREATE OR REPLACE FUNCTION create_receipt_tx(p_receipt jsonb, p_lines jsonb)
RETURNS bigint LANGUAGE plpgsql AS $$
DECLARE
  v_receipt_id bigint;
  v_line jsonb;
  v_stock_id bigint;
BEGIN
  INSERT INTO receipt ("dateTime", supplier_id, reference, note, user_id)
  VALUES (
    COALESCE((p_receipt->>'dateTime')::timestamptz, now()),
    (p_receipt->>'supplier_id')::bigint,
    p_receipt->>'reference',
    p_receipt->>'note',
    (p_receipt->>'user_id')::bigint
  )
  RETURNING id INTO v_receipt_id;

  FOR v_line IN SELECT * FROM jsonb_array_elements(p_lines) LOOP
    INSERT INTO stock (item_id, location_id, quantity)
    VALUES ((v_line->>'item_id')::bigint, (v_line->>'location_id')::bigint, 0)
    ON CONFLICT (item_id, location_id) DO NOTHING;

    SELECT id INTO v_stock_id FROM stock
    WHERE item_id = (v_line->>'item_id')::bigint
      AND location_id = (v_line->>'location_id')::bigint;

    INSERT INTO receipt_stock (receipt_id, stock_id, quantity, unit_price, currency_id, supplier_id)
    VALUES (v_receipt_id, v_stock_id,
            (v_line->>'quantity')::int, (v_line->>'unit_price')::numeric,
            (v_line->>'currency_id')::bigint, (v_line->>'supplier_id')::bigint);

    UPDATE stock SET quantity = quantity + (v_line->>'quantity')::int WHERE id = v_stock_id;
  END LOOP;

  RETURN v_receipt_id;
END; $$;

-- 2c. Atomic sale voiding.
CREATE OR REPLACE FUNCTION void_sale_tx(
  p_sale_id bigint,
  p_user_id bigint,
  p_reason text
) RETURNS void LANGUAGE plpgsql AS $$
DECLARE
  v_line record;
BEGIN
  FOR v_line IN
    SELECT stock_id, quantity FROM sale_stock WHERE sale_id = p_sale_id
  LOOP
    IF v_line.stock_id IS NOT NULL AND v_line.quantity > 0 THEN
      UPDATE stock SET quantity = quantity + v_line.quantity WHERE id = v_line.stock_id;
    END IF;
  END LOOP;

  UPDATE sale SET
    status = 'VOIDED',
    void_reason = p_reason,
    voided_at = now(),
    voided_by = p_user_id
  WHERE id = p_sale_id;
END; $$;

-- 2d. Atomic receipt voiding.
CREATE OR REPLACE FUNCTION void_receipt_tx(
  p_receipt_id bigint,
  p_user_id bigint,
  p_reason text
) RETURNS void LANGUAGE plpgsql AS $$
DECLARE
  v_line record;
BEGIN
  FOR v_line IN
    SELECT stock_id, quantity FROM receipt_stock WHERE receipt_id = p_receipt_id
  LOOP
    IF v_line.stock_id IS NOT NULL AND v_line.quantity > 0 THEN
      UPDATE stock SET quantity = quantity - v_line.quantity WHERE id = v_line.stock_id;
    END IF;
  END LOOP;

  UPDATE receipt SET
    status = 'VOIDED',
    void_reason = p_reason,
    voided_at = now(),
    voided_by = p_user_id
  WHERE id = p_receipt_id;
END; $$;

-- 2e. Update transfer_stock RPC to populate from_item_id / to_item_id.
CREATE OR REPLACE FUNCTION transfer_stock(
  p_from_stock_id bigint,
  p_to_location_id bigint,
  p_quantity int,
  p_user_id bigint DEFAULT NULL,
  p_notes text DEFAULT NULL
) RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
  v_from_stock record;
  v_to_stock_id bigint;
  v_transfer_id bigint;
BEGIN
  SELECT id, item_id, location_id, quantity
    INTO v_from_stock
    FROM stock
   WHERE id = p_from_stock_id
     FOR UPDATE;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'Source stock row % not found', p_from_stock_id;
  END IF;

  IF v_from_stock.quantity < p_quantity THEN
    RAISE EXCEPTION 'Insufficient quantity: available %, requested %',
      v_from_stock.quantity, p_quantity;
  END IF;

  IF v_from_stock.location_id = p_to_location_id THEN
    RAISE EXCEPTION 'Source and destination locations must be different';
  END IF;

  IF NOT EXISTS (SELECT 1 FROM location WHERE id = p_to_location_id) THEN
    RAISE EXCEPTION 'Destination location % not found', p_to_location_id;
  END IF;

  UPDATE stock
     SET quantity = quantity - p_quantity
   WHERE id = p_from_stock_id;

  SELECT id INTO v_to_stock_id
    FROM stock
   WHERE item_id = v_from_stock.item_id
     AND location_id = p_to_location_id
     FOR UPDATE;

  IF v_to_stock_id IS NULL THEN
    INSERT INTO stock (item_id, location_id, quantity)
    VALUES (v_from_stock.item_id, p_to_location_id, p_quantity)
    RETURNING id INTO v_to_stock_id;
  ELSE
    UPDATE stock
       SET quantity = quantity + p_quantity
     WHERE id = v_to_stock_id;
  END IF;

  INSERT INTO transfer (stock_id_from_id, stock_id_to_id, quantity, date, user_id, notes, from_item_id, to_item_id)
  VALUES (p_from_stock_id, v_to_stock_id, p_quantity, now(), p_user_id, p_notes,
          v_from_stock.item_id, v_from_stock.item_id)
  RETURNING id INTO v_transfer_id;

  RETURN jsonb_build_object(
    'id', v_transfer_id,
    'stock_id_from_id', p_from_stock_id,
    'stock_id_to_id', v_to_stock_id,
    'quantity', p_quantity,
    'user_id', p_user_id,
    'notes', p_notes
  );
END;
$$;
