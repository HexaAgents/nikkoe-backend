import type { DbClient } from "../types/db.types.js";
import type {
  Sale,
  SaleLine,
  SaleWithRelations,
  SaleInput,
  SaleLineInput,
} from "../types/domain.types.js";
import type { PaginationParams, PaginatedResult } from "../types/pagination.types.js";
import type { ISaleRepository } from "./interfaces.js";
import { batchLoad } from "./utils/batchLoad.js";

export function createSaleRepository(db: DbClient): ISaleRepository {
  return {
    async findAll(pagination?: PaginationParams): Promise<PaginatedResult<SaleWithRelations>> {
      let query = db
        .from("sales")
        .select("*", { count: "exact" })
        .order("sold_at", { ascending: false });

      if (pagination) {
        query = query.range(pagination.offset, pagination.offset + pagination.limit - 1);
      }

      const { data: sales, error, count } = await query;

      if (error) throw error;
      if (!sales || sales.length === 0) return { data: [], total: count ?? 0 };

      const channelIds = [
        ...new Set(sales.map((s) => s.channel_id).filter(Boolean)),
      ] as string[];
      const userIds = [
        ...new Set(sales.map((s) => s.sold_by).filter(Boolean)),
      ] as string[];

      const [channelsById, usersById] = await Promise.all([
        batchLoad(db, "channels", "channel_id", channelIds, "channel_id, channel_name"),
        batchLoad(db, "users", "user_id", userIds, "user_id, name"),
      ]);

      const data = sales.map((s) => ({
        ...s,
        channels: s.channel_id
          ? channelsById.get(s.channel_id) || null
          : null,
        users: s.sold_by ? usersById.get(s.sold_by) || null : null,
      }));

      return { data, total: count ?? 0 };
    },

    async findById(id: string) {
      const { data, error } = await db
        .from("sales")
        .select("*, channels(channel_name), users(name)")
        .eq("sale_id", id)
        .maybeSingle();

      if (error) throw error;
      return data ?? null;
    },

    async findLines(saleId: string): Promise<SaleLine[]> {
      const { data, error } = await db
        .from("sale_lines")
        .select("*, items(part_number), locations(location_code)")
        .eq("sale_id", saleId)
        .order("created_at");

      if (error) throw error;
      return data ?? [];
    },

    async findByItemId(itemId: string) {
      const { data, error } = await db
        .from("sale_lines")
        .select("*, sales(sale_id, sold_at), locations(location_code)")
        .eq("item_id", itemId)
        .order("created_at", { ascending: false });

      if (error) throw error;
      return data ?? [];
    },

    async create(sale: SaleInput, lines: SaleLineInput[]): Promise<Sale> {
      const { data, error } = await db.rpc("create_sale", {
        p_sale: sale,
        p_lines: lines,
      });

      if (error) throw error;
      return data as unknown as Sale;
    },

    async voidSale(
      saleId: string,
      userId: string,
      reason?: string,
    ): Promise<void> {
      const { error } = await db.rpc("void_sale", {
        p_sale_id: saleId,
        p_voided_by: userId,
        p_reason: reason || null,
      });

      if (error) throw error;
    },
  };
}

export type SaleRepository = ISaleRepository;
