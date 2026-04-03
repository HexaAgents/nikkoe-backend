import type { DbClient } from "../types/db.types.js";
import type { Location, LocationInput } from "../types/domain.types.js";
import type { PaginationParams, PaginatedResult } from "../types/pagination.types.js";
import type { ILocationRepository } from "./interfaces.js";

export function createLocationRepository(db: DbClient): ILocationRepository {
  return {
    async findAll(pagination?: PaginationParams): Promise<PaginatedResult<Location>> {
      let query = db
        .from("locations")
        .select("*", { count: "exact" })
        .order("location_code");

      if (pagination) {
        query = query.range(pagination.offset, pagination.offset + pagination.limit - 1);
      }

      const { data, error, count } = await query;

      if (error) throw error;
      return { data: data ?? [], total: count ?? 0 };
    },

    async create(input: LocationInput): Promise<Location> {
      const { data, error } = await db
        .from("locations")
        .insert(input)
        .select()
        .single();

      if (error) throw error;
      return data;
    },

    async remove(id: string): Promise<void> {
      const { error } = await db
        .from("locations")
        .delete()
        .eq("location_id", id);

      if (error) throw error;
    },
  };
}

export type LocationRepository = ILocationRepository;
