-- Transactional application point for audited stock corrections.
--
-- The caller must provide the quantity observed during dry-run
-- (quantity_before). The RPC locks each stock row, verifies it has not changed,
-- rejects any adjustment that would leave a row negative, updates stock, and
-- writes one stock_adjustment row per stock row change.

CREATE OR REPLACE FUNCTION apply_stock_adjustment_batch(
  p_reason text,
  p_adjustments jsonb,
  p_created_by bigint DEFAULT NULL,
  p_metadata jsonb DEFAULT '{}'::jsonb
) RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
  v_batch_id bigint;
  v_adjustment jsonb;
  v_stock record;
  v_stock_id bigint;
  v_item_id bigint;
  v_location_id bigint;
  v_delta int;
  v_before int;
  v_after int;
  v_reason text;
  v_source text;
  v_row_count int := 0;
  v_item_count int := 0;
  v_total_delta int := 0;
BEGIN
  IF p_reason IS NULL OR btrim(p_reason) = '' THEN
    RAISE EXCEPTION 'Adjustment batch reason is required' USING ERRCODE = 'check_violation';
  END IF;

  IF p_adjustments IS NULL OR jsonb_typeof(p_adjustments) <> 'array' THEN
    RAISE EXCEPTION 'p_adjustments must be a JSON array' USING ERRCODE = 'check_violation';
  END IF;

  IF jsonb_array_length(p_adjustments) = 0 THEN
    RAISE EXCEPTION 'p_adjustments must contain at least one adjustment' USING ERRCODE = 'check_violation';
  END IF;

  CREATE TEMP TABLE _stock_adjustment_items(item_id bigint PRIMARY KEY) ON COMMIT DROP;

  INSERT INTO stock_adjustment_batch (created_by, reason, mode, metadata)
  VALUES (p_created_by, p_reason, 'APPLIED', COALESCE(p_metadata, '{}'::jsonb))
  RETURNING id INTO v_batch_id;

  FOR v_adjustment IN SELECT * FROM jsonb_array_elements(p_adjustments) LOOP
    v_stock_id := (v_adjustment->>'stock_id')::bigint;
    v_delta := (v_adjustment->>'quantity_delta')::int;
    v_before := (v_adjustment->>'quantity_before')::int;
    v_reason := COALESCE(NULLIF(v_adjustment->>'reason', ''), p_reason);
    v_source := COALESCE(NULLIF(v_adjustment->>'source', ''), 'MISMATCH_RECONCILIATION');

    IF v_delta = 0 THEN
      RAISE EXCEPTION 'Adjustment for stock row % has zero delta', v_stock_id
        USING ERRCODE = 'check_violation';
    END IF;

    SELECT id, item_id, location_id, quantity
      INTO v_stock
      FROM stock
     WHERE id = v_stock_id
     FOR UPDATE;

    IF NOT FOUND THEN
      RAISE EXCEPTION 'Stock row % not found', v_stock_id
        USING ERRCODE = 'foreign_key_violation';
    END IF;

    IF v_stock.quantity <> v_before THEN
      RAISE EXCEPTION 'Stale stock quantity for stock row %: expected %, found %',
        v_stock_id, v_before, v_stock.quantity
        USING ERRCODE = 'check_violation';
    END IF;

    v_after := v_stock.quantity + v_delta;
    IF v_after < 0 THEN
      RAISE EXCEPTION 'Adjustment would leave stock row % negative: before %, delta %, after %',
        v_stock_id, v_stock.quantity, v_delta, v_after
        USING ERRCODE = 'check_violation';
    END IF;

    UPDATE stock
       SET quantity = v_after
     WHERE id = v_stock_id;

    v_item_id := COALESCE((v_adjustment->>'item_id')::bigint, v_stock.item_id);
    v_location_id := COALESCE((v_adjustment->>'location_id')::bigint, v_stock.location_id);

    IF v_item_id <> v_stock.item_id OR v_location_id <> v_stock.location_id THEN
      RAISE EXCEPTION 'Adjustment identity mismatch for stock row %', v_stock_id
        USING ERRCODE = 'check_violation';
    END IF;

    INSERT INTO stock_adjustment (
      batch_id,
      stock_id,
      item_id,
      location_id,
      quantity_delta,
      quantity_before,
      quantity_after,
      reason,
      source
    )
    VALUES (
      v_batch_id,
      v_stock_id,
      v_stock.item_id,
      v_stock.location_id,
      v_delta,
      v_before,
      v_after,
      v_reason,
      v_source
    );

    INSERT INTO _stock_adjustment_items(item_id)
    VALUES (v_stock.item_id)
    ON CONFLICT DO NOTHING;

    v_row_count := v_row_count + 1;
    v_total_delta := v_total_delta + v_delta;
  END LOOP;

  SELECT COUNT(*) INTO v_item_count FROM _stock_adjustment_items;

  RETURN jsonb_build_object(
    'batch_id', v_batch_id,
    'adjusted_items', v_item_count,
    'adjusted_rows', v_row_count,
    'total_delta', v_total_delta
  );
END;
$$;
