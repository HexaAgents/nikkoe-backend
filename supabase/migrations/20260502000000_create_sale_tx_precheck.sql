-- Replace create_sale_tx with a version that prechecks stock availability per line.
-- Previously, the RPC inserted a stock row at quantity 0 (via ON CONFLICT DO NOTHING)
-- and then decremented unconditionally, which silently drove the row negative when
-- a sale arrived for a location that had no on-hand. That broke the
-- "Total Quantity == SUM(visible Locations)" invariant on the item detail page.
--
-- This version:
--   * Resolves (item_id, location_id) -> stock row with FOR UPDATE so concurrent
--     sales serialize correctly.
--   * Refuses to create a 0-quantity stock row for sale lines that would oversell.
--   * Raises with SQLSTATE 'check_violation' (23514) and a message starting with
--     "Insufficient stock" so the FastAPI layer can surface a clean 400.
--
-- The void_sale_tx, create_receipt_tx, void_receipt_tx, and transfer_stock RPCs
-- from 20260421010004_transactional_rpcs.sql remain unchanged.

CREATE OR REPLACE FUNCTION create_sale_tx(p_sale jsonb, p_lines jsonb)
RETURNS bigint LANGUAGE plpgsql AS $$
DECLARE
  v_sale_id bigint;
  v_line jsonb;
  v_stock_id bigint;
  v_available int;
  v_requested int;
  v_item_id bigint;
  v_location_id bigint;
BEGIN
  -- Pre-validate every line BEFORE inserting the sale, so a single oversell
  -- aborts the whole transaction without leaving phantom stock rows behind.
  FOR v_line IN SELECT * FROM jsonb_array_elements(p_lines) LOOP
    v_item_id := (v_line->>'item_id')::bigint;
    v_location_id := (v_line->>'location_id')::bigint;
    v_requested := (v_line->>'quantity')::int;

    SELECT id, quantity INTO v_stock_id, v_available
      FROM stock
     WHERE item_id = v_item_id
       AND location_id = v_location_id
       FOR UPDATE;

    IF v_stock_id IS NULL THEN
      v_available := 0;
    END IF;

    IF v_available < v_requested THEN
      RAISE EXCEPTION
        'Insufficient stock for item % at location %: available %, requested %',
        v_item_id, v_location_id, v_available, v_requested
        USING ERRCODE = 'check_violation';
    END IF;
  END LOOP;

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
    v_item_id := (v_line->>'item_id')::bigint;
    v_location_id := (v_line->>'location_id')::bigint;
    v_requested := (v_line->>'quantity')::int;

    -- Re-resolve the stock row (locked above by the precheck loop). It must exist
    -- with sufficient quantity; we are only inside the transaction that holds the
    -- row lock, so no other writer can have decremented it in between.
    SELECT id INTO v_stock_id FROM stock
    WHERE item_id = v_item_id
      AND location_id = v_location_id;

    INSERT INTO sale_stock (sale_id, stock_id, quantity, unit_price, currency_id)
    VALUES (v_sale_id, v_stock_id,
            v_requested, (v_line->>'unit_price')::numeric,
            (v_line->>'currency_id')::bigint);

    UPDATE stock SET quantity = quantity - v_requested WHERE id = v_stock_id;
  END LOOP;

  RETURN v_sale_id;
END; $$;
