import type { DbClient } from "../types/db.types.js";
import type { Supplier, SupplierInput } from "../types/domain.types.js";
import type { PaginationParams, PaginatedResult } from "../types/pagination.types.js";
import type { ISupplierRepository } from "./interfaces.js";

export function createSupplierRepository(db: DbClient): ISupplierRepository {
  return {
    async findAll(pagination?: PaginationParams): Promise<PaginatedResult<Supplier>> {
      let query = db
        .from("suppliers")
        .select("*", { count: "exact" })
        .order("supplier_name");

      if (pagination) {
        query = query.range(pagination.offset, pagination.offset + pagination.limit - 1);
      }

      const { data, error, count } = await query;

      if (error) throw error;
      return { data: data ?? [], total: count ?? 0 };
    },

    async create(input: SupplierInput): Promise<Supplier> {
      const { data, error } = await db
        .from("suppliers")
        .insert(input)
        .select()
        .single();

      if (error) throw error;
      return data;
    },

    async remove(id: string): Promise<void> {
      const { error } = await db
        .from("suppliers")
        .delete()
        .eq("supplier_id", id);

      if (error) throw error;
    },
  };
}

export type SupplierRepository = ISupplierRepository;
