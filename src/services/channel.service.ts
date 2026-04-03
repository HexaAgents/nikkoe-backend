import type { ChannelRepository } from "../repositories/channel.repository.js";
import type { IChannelService } from "./interfaces.js";
import type { PaginationParams } from "../types/pagination.types.js";

export function createChannelService(repo: ChannelRepository): IChannelService {
  return {
    async listChannels(pagination?: PaginationParams) {
      return repo.findAll(pagination);
    },
  };
}

export type ChannelService = IChannelService;
