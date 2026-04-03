import type { LocationRepository } from "../repositories/location.repository.js";
import type { ILocationService } from "./interfaces.js";
import type { PaginationParams } from "../types/pagination.types.js";
import { locationInputSchema } from "../schemas/index.js";

export function createLocationService(repo: LocationRepository): ILocationService {
  return {
    async listLocations(pagination?: PaginationParams) {
      return repo.findAll(pagination);
    },

    async createLocation(body: unknown) {
      const validated = locationInputSchema.parse(body);
      return repo.create(validated);
    },

    async deleteLocation(id: string) {
      return repo.remove(id);
    },
  };
}

export type LocationService = ILocationService;
