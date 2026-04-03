import type { DbClient } from "../types/db.types.js";
import type { Customer, CustomerInput } from "../types/domain.types.js";
import type { PaginationParams, PaginatedResult } from "../types/pagination.types.js";
import type { ICustomerRepository } from "./interfaces.js";

export function createCustomerRepository(db: DbClient): ICustomerRepository {
  return {
    async findAll(pagination?: PaginationParams): Promise<PaginatedResult<Customer>> {
      let query = db
        .from("customer")
        .select("customer_id, name", { count: "exact" })
        .order("name");

      if (pagination) {
        query = query.range(pagination.offset, pagination.offset + pagination.limit - 1);
      }

      const { data, error, count } = await query;

      if (error) throw error;
      return { data: data ?? [], total: count ?? 0 };
    },

    async create(input: CustomerInput): Promise<Customer> {
      const { data, error } = await db
        .from("customer")
        .insert({ name: input.name })
        .select("customer_id, name")
        .single();

      if (error) throw error;
      return data;
    },
  };
}

export type CustomerRepository = ICustomerRepository;
