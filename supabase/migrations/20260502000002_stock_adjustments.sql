-- Audit trail for stock reconciliation and manual stock corrections.
--
-- These tables intentionally do not replace receipt/sale/transfer history.
-- They record explicit, auditable corrections used when historical stock rows
-- are inconsistent (for example: a placeholder location contains negative
-- stock while a real location contains positive stock for the same item).

CREATE TABLE IF NOT EXISTS stock_adjustment_batch (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    created_at  timestamptz NOT NULL DEFAULT now(),
    created_by  bigint REFERENCES "user"(id) ON DELETE SET NULL,
    reason      text NOT NULL,
    mode        text NOT NULL DEFAULT 'APPLIED',
    metadata    jsonb NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT chk_stock_adjustment_batch_mode CHECK (mode IN ('DRY_RUN', 'APPLIED'))
);

CREATE TABLE IF NOT EXISTS stock_adjustment (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    batch_id        bigint NOT NULL REFERENCES stock_adjustment_batch(id) ON DELETE CASCADE,
    stock_id        bigint NOT NULL REFERENCES stock(id) ON DELETE RESTRICT,
    item_id         bigint NOT NULL REFERENCES item(id) ON DELETE RESTRICT,
    location_id     bigint NOT NULL REFERENCES location(id) ON DELETE RESTRICT,
    quantity_delta  int NOT NULL,
    quantity_before int NOT NULL,
    quantity_after  int NOT NULL,
    reason          text NOT NULL,
    source          text NOT NULL DEFAULT 'MISMATCH_RECONCILIATION',
    created_at      timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT chk_stock_adjustment_nonzero_delta CHECK (quantity_delta <> 0),
    CONSTRAINT chk_stock_adjustment_math CHECK (quantity_after = quantity_before + quantity_delta)
);

CREATE INDEX IF NOT EXISTS idx_stock_adjustment_batch_created_at
    ON stock_adjustment_batch(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_stock_adjustment_batch_created_by
    ON stock_adjustment_batch(created_by);
CREATE INDEX IF NOT EXISTS idx_stock_adjustment_batch_mode
    ON stock_adjustment_batch(mode);

CREATE INDEX IF NOT EXISTS idx_stock_adjustment_batch_id
    ON stock_adjustment(batch_id);
CREATE INDEX IF NOT EXISTS idx_stock_adjustment_stock_id
    ON stock_adjustment(stock_id);
CREATE INDEX IF NOT EXISTS idx_stock_adjustment_item_id
    ON stock_adjustment(item_id);
CREATE INDEX IF NOT EXISTS idx_stock_adjustment_location_id
    ON stock_adjustment(location_id);
CREATE INDEX IF NOT EXISTS idx_stock_adjustment_created_at
    ON stock_adjustment(created_at DESC);
