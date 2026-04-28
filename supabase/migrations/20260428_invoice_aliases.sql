-- Persistent mappings used by the invoice parser to auto-resolve future
-- invoices once the user has manually matched a supplier name or part number.
--
-- 1. supplier_alias: free-form alias text → canonical supplier id.
--    Used when an invoice's "supplier_name" string consistently differs from
--    the canonical name in the supplier table (e.g. "Premier Farnell UK Ltd"
--    on the invoice, "Farnell" in the database).
--
-- 2. item_supplier.supplier_part_number: the part number a given supplier
--    prints on its invoices for our item. Lives on the existing item_supplier
--    row so it sits alongside cost/currency for that (item, supplier) pair.

CREATE TABLE IF NOT EXISTS supplier_alias (
    id          BIGSERIAL PRIMARY KEY,
    alias       TEXT NOT NULL,
    supplier_id BIGINT NOT NULL REFERENCES supplier(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by  BIGINT REFERENCES "user"(id) ON DELETE SET NULL
);

-- Aliases are matched case-insensitively, so enforce uniqueness on lower(alias).
CREATE UNIQUE INDEX IF NOT EXISTS uq_supplier_alias_lower
    ON supplier_alias (LOWER(alias));

CREATE INDEX IF NOT EXISTS idx_supplier_alias_supplier_id
    ON supplier_alias (supplier_id);

ALTER TABLE item_supplier
    ADD COLUMN IF NOT EXISTS supplier_part_number TEXT;

-- (supplier_id, supplier_part_number) must point to a single item — that's the
-- whole purpose of the alias. Partial index so legacy rows with NULL part
-- numbers don't trip the constraint.
CREATE UNIQUE INDEX IF NOT EXISTS uq_item_supplier_part_number
    ON item_supplier (supplier_id, supplier_part_number)
    WHERE supplier_part_number IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_item_supplier_supplier_id
    ON item_supplier (supplier_id);
