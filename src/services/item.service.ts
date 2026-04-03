import type { ItemRepository } from "../repositories/item.repository.js";
import type { SupplierQuoteRepository } from "../repositories/supplierQuote.repository.js";
import type { InventoryRepository } from "../repositories/inventory.repository.js";
import type { ReceiptRepository } from "../repositories/receipt.repository.js";
import type { SaleRepository } from "../repositories/sale.repository.js";
import type { IItemService } from "./interfaces.js";
import type { PaginationParams } from "../types/pagination.types.js";
import { itemInputSchema } from "../schemas/index.js";
import { NotFoundError } from "../errors/index.js";

export function createItemService(
  repo: ItemRepository,
  quoteRepo: SupplierQuoteRepository,
  inventoryRepo: InventoryRepository,
  receiptRepo: ReceiptRepository,
  saleRepo: SaleRepository,
): IItemService {
  return {
    async listItems(pagination?: PaginationParams) {
      return repo.findAll(pagination);
    },

    async getItem(id: string) {
      const item = await repo.findById(id);
      if (!item) throw new NotFoundError("Item", id);
      return item;
    },

    async getItemQuotes(itemId: string) {
      return quoteRepo.findByItemId(itemId);
    },

    async getItemInventory(itemId: string) {
      return inventoryRepo.findByItemId(itemId);
    },

    async getItemReceipts(itemId: string) {
      return receiptRepo.findByItemId(itemId);
    },

    async getItemSales(itemId: string) {
      return saleRepo.findByItemId(itemId);
    },

    async createItem(body: unknown) {
      const validated = itemInputSchema.parse(body);
      return repo.create(validated);
    },

    async updateItem(id: string, body: unknown) {
      const validated = itemInputSchema.partial().parse(body);
      return repo.update(id, validated);
    },

    async deleteItem(id: string) {
      return repo.remove(id);
    },
  };
}

export type ItemService = IItemService;
