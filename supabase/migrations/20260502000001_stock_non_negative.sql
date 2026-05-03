-- Defense in depth: forbid negative stock at the database level.
--
-- Application code now prechecks availability on every write path
-- (create_sale_tx RPC, SaleRepository._create_fallback, EbaySyncService),
-- but a CHECK constraint guarantees the invariant even if a future
-- writer forgets, gets refactored, or is exercised via raw SQL.
--
-- Added as NOT VALID so this migration applies cleanly against environments
-- that still have legacy negative rows (the audit script
-- scripts/audit_stock_discrepancies.py enumerates them; cleanup is a
-- per-environment business decision, not a deploy-time decision).
--
-- After cleanup is performed for a given environment, run:
--
--     ALTER TABLE stock VALIDATE CONSTRAINT chk_stock_non_negative;
--
-- to retroactively prove every existing row satisfies the constraint. New
-- INSERTs and UPDATEs are checked immediately regardless of NOT VALID.

DO $$ BEGIN
  ALTER TABLE stock
    ADD CONSTRAINT chk_stock_non_negative CHECK (quantity >= 0) NOT VALID;
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;
