-- Add void/status columns to Sale table
ALTER TABLE "Sale" ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'ACTIVE';
ALTER TABLE "Sale" ADD COLUMN IF NOT EXISTS void_reason text;
ALTER TABLE "Sale" ADD COLUMN IF NOT EXISTS voided_at timestamptz;
ALTER TABLE "Sale" ADD COLUMN IF NOT EXISTS voided_by bigint REFERENCES "User"(id);
ALTER TABLE "Sale" ADD COLUMN IF NOT EXISTS note text;

-- Add void/status columns to Receipt table
ALTER TABLE "Receipt" ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'ACTIVE';
ALTER TABLE "Receipt" ADD COLUMN IF NOT EXISTS void_reason text;
ALTER TABLE "Receipt" ADD COLUMN IF NOT EXISTS voided_at timestamptz;
ALTER TABLE "Receipt" ADD COLUMN IF NOT EXISTS voided_by bigint REFERENCES "User"(id);
ALTER TABLE "Receipt" ADD COLUMN IF NOT EXISTS note text;
ALTER TABLE "Receipt" ADD COLUMN IF NOT EXISTS reference text;
ALTER TABLE "Receipt" ADD COLUMN IF NOT EXISTS supplier_id bigint REFERENCES "Supplier"(id);
