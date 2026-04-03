import type { SupplierQuoteRepository } from "../repositories/supplierQuote.repository.js";
import type { ISupplierQuoteService } from "./interfaces.js";
import { quoteInputSchema } from "../schemas/index.js";

export function createSupplierQuoteService(repo: SupplierQuoteRepository): ISupplierQuoteService {
  return {
    async createQuote(body: unknown) {
      const validated = quoteInputSchema.parse(body);
      return repo.create(validated);
    },

    async deleteQuote(id: string) {
      return repo.remove(id);
    },
  };
}

export type SupplierQuoteService = ISupplierQuoteService;
