import { z } from "zod";
import type { ReceiptRepository } from "../repositories/receipt.repository.js";
import type { IReceiptService } from "./interfaces.js";
import type { PaginationParams } from "../types/pagination.types.js";
import {
  receiptInputSchema,
  receiptLineSchema,
} from "../schemas/index.js";
import { NotFoundError } from "../errors/index.js";

export function createReceiptService(repo: ReceiptRepository): IReceiptService {
  return {
    async listReceipts(pagination?: PaginationParams) {
      return repo.findAll(pagination);
    },

    async getReceipt(id: string) {
      const receipt = await repo.findById(id);
      if (!receipt) throw new NotFoundError("Receipt", id);
      return receipt;
    },

    async getReceiptLines(receiptId: string) {
      return repo.findLines(receiptId);
    },

    async createReceipt(body: { receipt: unknown; lines: unknown }) {
      const receipt = receiptInputSchema.parse(body.receipt);
      const lines = z.array(receiptLineSchema).parse(body.lines);
      return repo.create(receipt, lines);
    },

    async voidReceipt(receiptId: string, userId: string, reason?: string) {
      return repo.voidReceipt(receiptId, userId, reason);
    },
  };
}

export type ReceiptService = IReceiptService;
