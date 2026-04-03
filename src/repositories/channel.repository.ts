import type { DbClient } from "../types/db.types.js";
import type { Channel } from "../types/domain.types.js";
import type { PaginationParams, PaginatedResult } from "../types/pagination.types.js";
import type { IChannelRepository } from "./interfaces.js";

export function createChannelRepository(db: DbClient): IChannelRepository {
  return {
    async findAll(pagination?: PaginationParams): Promise<PaginatedResult<Channel>> {
      let query = db
        .from("channels")
        .select("*", { count: "exact" })
        .order("channel_name");

      if (pagination) {
        query = query.range(pagination.offset, pagination.offset + pagination.limit - 1);
      }

      const { data, error, count } = await query;

      if (error) throw error;
      return { data: data ?? [], total: count ?? 0 };
    },
  };
}

export type ChannelRepository = IChannelRepository;
