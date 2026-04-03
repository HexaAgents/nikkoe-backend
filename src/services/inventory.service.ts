import type { InventoryRepository } from "../repositories/inventory.repository.js";
import type { IInventoryService } from "./interfaces.js";
import type { PaginationParams } from "../types/pagination.types.js";

export function createInventoryService(repo: InventoryRepository): IInventoryService {
  return {
    async listMovements(pagination?: PaginationParams) {
      return repo.findMovements(pagination);
    },

    async listOnHand() {
      return repo.findOnHand();
    },
  };
}

export type InventoryService = IInventoryService;
