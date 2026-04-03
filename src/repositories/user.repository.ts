import type { DbClient } from "../types/db.types.js";
import type { CreatedUser, CreateUserInput } from "../types/domain.types.js";
import type { IUserRepository } from "./interfaces.js";

export function createUserRepository(db: DbClient): IUserRepository {
  return {
    async createAuthUser(input: CreateUserInput): Promise<CreatedUser> {
      const { data, error } = await db.auth.admin.createUser({
        email: input.email,
        password: input.password,
        email_confirm: true,
      });

      if (error) {
        throw new Error(error.message);
      }

      return { id: data.user.id, email: data.user.email };
    },
  };
}

export type UserRepository = IUserRepository;
