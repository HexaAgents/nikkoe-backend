import type { CustomerRepository } from "../repositories/customer.repository.js";
import type { ICustomerService } from "./interfaces.js";
import type { PaginationParams } from "../types/pagination.types.js";
import { customerInputSchema } from "../schemas/index.js";

export function createCustomerService(repo: CustomerRepository): ICustomerService {
  return {
    async listCustomers(pagination?: PaginationParams) {
      return repo.findAll(pagination);
    },

    async createCustomer(body: unknown) {
      const validated = customerInputSchema.parse(body);
      return repo.create(validated);
    },
  };
}

export type CustomerService = ICustomerService;
