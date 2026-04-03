import type { DbClient } from "../types/db.types.js";
import type {
  SupplierQuote,
  SupplierQuoteInput,
} from "../types/domain.types.js";
import type { ISupplierQuoteRepository } from "./interfaces.js";

export function createSupplierQuoteRepository(db: DbClient): ISupplierQuoteRepository {
  return {
    async findByItemId(itemId: string) {
      const { data, error } = await db
        .from("supplier_quotes")
        .select("*, suppliers(supplier_name)")
        .eq("item_id", itemId)
        .order("quoted_at", { ascending: false });

      if (error) throw error;
      return data ?? [];
    },

    async create(input: SupplierQuoteInput): Promise<SupplierQuote> {
      const { data, error } = await db
        .from("supplier_quotes")
        .insert(input)
        .select()
        .single();

      if (error) throw error;
      return data;
    },

    async remove(id: string): Promise<void> {
      const { error } = await db
        .from("supplier_quotes")
        .delete()
        .eq("quote_id", id);

      if (error) throw error;
    },
  };
}

export type SupplierQuoteRepository = ISupplierQuoteRepository;
