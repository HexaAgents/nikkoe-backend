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

  INSERT INTO transfer (stock_id_from_id, stock_id_to_id, quantity, date, user_id, notes)
  VALUES (p_from_stock_id, v_to_stock_id, p_quantity, now(), p_user_id, p_notes)
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
