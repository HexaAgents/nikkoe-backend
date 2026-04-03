import type { DbClient } from "../types/db.types.js";
import type { Category, CategoryInput } from "../types/domain.types.js";
import type { PaginationParams, PaginatedResult } from "../types/pagination.types.js";
import type { ICategoryRepository } from "./interfaces.js";

export function createCategoryRepository(db: DbClient): ICategoryRepository {
  return {
    async findAll(pagination?: PaginationParams): Promise<PaginatedResult<Category>> {
      let query = db
        .from("categories")
        .select("*", { count: "exact" })
        .order("name");

      if (pagination) {
        query = query.range(pagination.offset, pagination.offset + pagination.limit - 1);
      }

      const { data, error, count } = await query;

      if (error) throw error;
      return { data: data ?? [], total: count ?? 0 };
    },

    async create(input: CategoryInput): Promise<Category> {
      const { data, error } = await db
        .from("categories")
        .insert(input)
        .select()
        .single();

      if (error) throw error;
      return data;
    },

    async remove(id: string): Promise<void> {
      const { error } = await db
        .from("categories")
        .delete()
        .eq("category_id", id);

      if (error) throw error;
    },
  };
}

export type CategoryRepository = ICategoryRepository;
