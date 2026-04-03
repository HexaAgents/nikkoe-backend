import { z } from "zod";
import type { SaleRepository } from "../repositories/sale.repository.js";
import type { ISaleService } from "./interfaces.js";
import type { PaginationParams } from "../types/pagination.types.js";
import { saleInputSchema, saleLineSchema } from "../schemas/index.js";
import { NotFoundError } from "../errors/index.js";

export function createSaleService(repo: SaleRepository): ISaleService {
  return {
    async listSales(pagination?: PaginationParams) {
      return repo.findAll(pagination);
    },

    async getSale(id: string) {
      const sale = await repo.findById(id);
      if (!sale) throw new NotFoundError("Sale", id);
      return sale;
    },

    async getSaleLines(saleId: string) {
      return repo.findLines(saleId);
    },

    async createSale(body: { sale: unknown; lines: unknown }) {
      const sale = saleInputSchema.parse(body.sale);
      const lines = z.array(saleLineSchema).parse(body.lines);
      return repo.create(sale, lines);
    },

    async voidSale(saleId: string, userId: string, reason?: string) {
      return repo.voidSale(saleId, userId, reason);
    },
  };
}

export type SaleService = ISaleService;
