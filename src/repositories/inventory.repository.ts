import type { DbClient } from "../types/db.types.js";
import type {
  InventoryMovementWithRelations,
  InventoryBalance,
} from "../types/domain.types.js";
import type { PaginationParams, PaginatedResult } from "../types/pagination.types.js";
import type { IInventoryRepository } from "./interfaces.js";
import { batchLoad } from "./utils/batchLoad.js";

export function createInventoryRepository(db: DbClient): IInventoryRepository {
  return {
    async findMovements(pagination?: PaginationParams): Promise<PaginatedResult<InventoryMovementWithRelations>> {
      let query = db
        .from("inventory_movements")
        .select("*", { count: "exact" })
        .order("moved_at", { ascending: false });

      if (pagination) {
        query = query.range(pagination.offset, pagination.offset + pagination.limit - 1);
      }

      const { data: movements, error, count } = await query;

      if (error) throw error;
      if (!movements || movements.length === 0) return { data: [], total: count ?? 0 };

      const itemIds = [
        ...new Set(movements.map((m) => m.item_id).filter(Boolean)),
      ] as string[];
      const userIds = [
        ...new Set(movements.map((m) => m.user_id).filter(Boolean)),
      ] as string[];

      const [itemsById, usersById] = await Promise.all([
        batchLoad(db, "items", "item_id", itemIds, "item_id, part_number"),
        batchLoad(db, "users", "user_id", userIds, "user_id, name"),
      ]);

      const data = movements.map((m) => ({
        ...m,
        items: m.item_id ? itemsById.get(m.item_id) || null : null,
        users: m.user_id ? usersById.get(m.user_id) || null : null,
      }));

      return { data, total: count ?? 0 };
    },

    async findByItemId(itemId: string) {
      const { data, error } = await db
        .from("inventory_balances")
        .select("*, locations(location_code)")
        .eq("item_id", itemId);

      if (error) throw error;
      return data ?? [];
    },

    async findOnHand(): Promise<InventoryBalance[]> {
      const { data, error } = await db
        .from("inventory_balances")
        .select("*")
        .gt("quantity_on_hand", 0);

      if (error?.code === "PGRST205") return [];
      if (error) throw error;
      return data ?? [];
    },
  };
}

export type InventoryRepository = IInventoryRepository;
