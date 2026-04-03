import type { UserRepository } from "../repositories/user.repository.js";
import type { UserProfile } from "../types/domain.types.js";
import type { IUserService } from "./interfaces.js";
import { createUserSchema } from "../schemas/index.js";
import { NotFoundError } from "../errors/index.js";

export function createUserService(repo: UserRepository): IUserService {
  return {
    getProfile(profile: UserProfile | null | undefined) {
      if (!profile) throw new NotFoundError("User profile", "current");
      return profile;
    },

    async createUser(body: unknown) {
      const validated = createUserSchema.parse(body);
      return repo.createAuthUser(validated);
    },
  };
}

export type UserService = IUserService;
