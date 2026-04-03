import type { CategoryRepository } from "../repositories/category.repository.js";
import type { ICategoryService } from "./interfaces.js";
import type { PaginationParams } from "../types/pagination.types.js";
import { categoryInputSchema } from "../schemas/index.js";

export function createCategoryService(repo: CategoryRepository): ICategoryService {
  return {
    async listCategories(pagination?: PaginationParams) {
      return repo.findAll(pagination);
    },

    async createCategory(body: unknown) {
      const validated = categoryInputSchema.parse(body);
      return repo.create(validated);
    },

    async deleteCategory(id: string) {
      return repo.remove(id);
    },
  };
}

export type CategoryService = ICategoryService;
