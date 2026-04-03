import type { SupplierRepository } from "../repositories/supplier.repository.js";
import type { ISupplierService } from "./interfaces.js";
import type { PaginationParams } from "../types/pagination.types.js";
import { supplierInputSchema } from "../schemas/index.js";

export function createSupplierService(repo: SupplierRepository): ISupplierService {
  return {
    async listSuppliers(pagination?: PaginationParams) {
      return repo.findAll(pagination);
    },

    async createSupplier(body: unknown) {
      const validated = supplierInputSchema.parse(body);
      return repo.create(validated);
    },

    async deleteSupplier(id: string) {
      return repo.remove(id);
    },
  };
}

export type SupplierService = ISupplierService;
