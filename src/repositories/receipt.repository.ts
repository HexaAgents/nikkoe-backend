import type { DbClient } from "../types/db.types.js";
import type {
  Receipt,
  ReceiptLine,
  ReceiptWithRelations,
  ReceiptInput,
  ReceiptLineInput,
} from "../types/domain.types.js";
import type { PaginationParams, PaginatedResult } from "../types/pagination.types.js";
import type { IReceiptRepository } from "./interfaces.js";
import { batchLoad } from "./utils/batchLoad.js";

export function createReceiptRepository(db: DbClient): IReceiptRepository {
  return {
    async findAll(pagination?: PaginationParams): Promise<PaginatedResult<ReceiptWithRelations>> {
      let query = db
        .from("receipts")
        .select("*", { count: "exact" })
        .order("received_at", { ascending: false });

      if (pagination) {
        query = query.range(pagination.offset, pagination.offset + pagination.limit - 1);
      }

      const { data: receipts, error, count } = await query;

      if (error) throw error;
      if (!receipts || receipts.length === 0) return { data: [], total: count ?? 0 };

      const supplierIds = [
        ...new Set(receipts.map((r) => r.supplier_id).filter(Boolean)),
      ] as string[];
      const userIds = [
        ...new Set(receipts.map((r) => r.received_by).filter(Boolean)),
      ] as string[];

      const [suppliersById, usersById] = await Promise.all([
        batchLoad(db, "suppliers", "supplier_id", supplierIds, "supplier_id, supplier_name"),
        batchLoad(db, "users", "user_id", userIds, "user_id, name"),
      ]);

      const data = receipts.map((r) => ({
        ...r,
        suppliers: r.supplier_id
          ? suppliersById.get(r.supplier_id) || null
          : null,
        users: r.received_by ? usersById.get(r.received_by) || null : null,
      }));

      return { data, total: count ?? 0 };
    },

    async findById(id: string) {
      const { data: receipt, error } = await db
        .from("receipts")
        .select("*")
        .eq("receipt_id", id)
        .maybeSingle();

      if (error) throw error;
      if (!receipt) return null;

      const [suppliersResult, usersResult] = await Promise.all([
        receipt.supplier_id
          ? db
              .from("suppliers")
              .select("supplier_id, supplier_name")
              .eq("supplier_id", receipt.supplier_id)
              .maybeSingle()
          : { data: null, error: null },
        receipt.received_by
          ? db
              .from("users")
              .select("user_id, name")
              .eq("user_id", receipt.received_by)
              .maybeSingle()
          : { data: null, error: null },
      ]);

      return {
        ...receipt,
        suppliers: suppliersResult.data ?? null,
        users: usersResult.data ?? null,
      };
    },

    async findLines(receiptId: string): Promise<ReceiptLine[]> {
      const { data, error } = await db
        .from("receipt_lines")
        .select("*")
        .eq("receipt_id", receiptId)
        .order("created_at");

      if (error) throw error;
      return data ?? [];
    },

    async findByItemId(itemId: string) {
      const { data, error } = await db
        .from("receipt_lines")
        .select(
          "*, receipts(receipt_id, received_at, suppliers(supplier_name)), locations(location_code)",
        )
        .eq("item_id", itemId)
        .order("created_at", { ascending: false });

      if (error) throw error;
      return data ?? [];
    },

    async create(
      receipt: ReceiptInput,
      lines: ReceiptLineInput[],
    ): Promise<Receipt> {
      const { data, error } = await db.rpc("create_receipt", {
        p_receipt: receipt,
        p_lines: lines,
      });

      if (error) throw error;
      return data as unknown as Receipt;
    },

    async voidReceipt(
      receiptId: string,
      userId: string,
      reason?: string,
    ): Promise<void> {
      const { error } = await db.rpc("void_receipt", {
        p_receipt_id: receiptId,
        p_voided_by: userId,
        p_reason: reason || null,
      });

      if (error) throw error;
    },
  };
}

export type ReceiptRepository = IReceiptRepository;
