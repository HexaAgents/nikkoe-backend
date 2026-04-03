import type { DbClient } from "../types/db.types.js";
import type { Item, ItemInput, ItemWithRelations } from "../types/domain.types.js";
import type { PaginationParams, PaginatedResult } from "../types/pagination.types.js";
import type { IItemRepository } from "./interfaces.js";
import { batchLoad } from "./utils/batchLoad.js";

export function createItemRepository(db: DbClient): IItemRepository {
  return {
    async findAll(pagination?: PaginationParams): Promise<PaginatedResult<ItemWithRelations>> {
      let query = db
        .from("items")
        .select("*", { count: "exact" })
        .order("part_number");

      if (pagination) {
        query = query.range(pagination.offset, pagination.offset + pagination.limit - 1);
      }

      const { data: items, error, count } = await query;

      if (error) throw error;
      if (!items || items.length === 0) return { data: [], total: count ?? 0 };

      const itemIds = items.map((i) => i.item_id);
      const categoryIds = [
        ...new Set(items.map((i) => i.category_id).filter(Boolean)),
      ] as string[];

      const [categoriesById, balancesResult, receiptLinesResult] =
        await Promise.all([
          batchLoad(db, "categories", "category_id", categoryIds, "category_id, name"),
          db
            .from("inventory_balances")
            .select("item_id, quantity_on_hand, location_id")
            .in("item_id", itemIds),
          db
            .from("receipt_lines")
            .select("item_id, unit_cost, receipt_id")
            .in("item_id", itemIds),
        ]);

      const locationIds = [
        ...new Set(
          (balancesResult.data || []).map((b) => b.location_id).filter(Boolean),
        ),
      ] as string[];
      const receiptIds = [
        ...new Set(
          (receiptLinesResult.data || [])
            .map((l) => l.receipt_id)
            .filter(Boolean),
        ),
      ] as string[];

      const [locationsById, receiptsById] = await Promise.all([
        batchLoad(db, "locations", "location_id", locationIds, "location_id, location_code"),
        batchLoad(db, "receipts", "receipt_id", receiptIds, "receipt_id, status"),
      ]);

      const balancesByItemId = new Map<string, unknown[]>();
      for (const b of balancesResult.data || []) {
        const arr = balancesByItemId.get(b.item_id) || [];
        arr.push({
          quantity_on_hand: b.quantity_on_hand,
          locations: b.location_id
            ? locationsById.get(b.location_id) || null
            : null,
        });
        balancesByItemId.set(b.item_id, arr);
      }

      const receiptLinesByItemId = new Map<string, unknown[]>();
      for (const l of receiptLinesResult.data || []) {
        const arr = receiptLinesByItemId.get(l.item_id) || [];
        arr.push({
          unit_cost: l.unit_cost,
          receipts: l.receipt_id
            ? receiptsById.get(l.receipt_id) || null
            : null,
        });
        receiptLinesByItemId.set(l.item_id, arr);
      }

      const data = items.map((item) => ({
        ...item,
        categories: item.category_id
          ? categoriesById.get(item.category_id) || null
          : null,
        inventory_balances: (balancesByItemId.get(item.item_id) || []) as ItemWithRelations["inventory_balances"],
        receipt_lines: (receiptLinesByItemId.get(item.item_id) || []) as ItemWithRelations["receipt_lines"],
      }));

      return { data, total: count ?? 0 };
    },

    async findById(id: string) {
      const { data, error } = await db
        .from("items")
        .select("*, categories(name)")
        .eq("item_id", id)
        .maybeSingle();

      if (error) throw error;
      return data ?? null;
    },

    async create(input: ItemInput): Promise<Item> {
      const { data, error } = await db
        .from("items")
        .insert(input)
        .select()
        .single();

      if (error) throw error;
      return data;
    },

    async update(id: string, input: Partial<ItemInput>): Promise<Item> {
      const { data, error } = await db
        .from("items")
        .update(input)
        .eq("item_id", id)
        .select()
        .single();

      if (error) throw error;
      return data;
    },

    async remove(id: string): Promise<void> {
      const { error } = await db
        .from("items")
        .delete()
        .eq("item_id", id);

      if (error) throw error;
    },
  };
}

export type ItemRepository = IItemRepository;
