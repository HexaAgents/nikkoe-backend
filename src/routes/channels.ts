import { Router, Request, Response } from "express";
import type { ChannelService } from "../services/channel.service.js";
import { asyncHandler } from "../middleware/asyncHandler.js";
import { paginationSchema } from "../schemas/index.js";

export function createChannelRouter(service: ChannelService): Router {
  const router = Router();

  router.get("/", asyncHandler(async (req: Request, res: Response) => {
    const pagination = paginationSchema.parse(req.query);
    res.json(await service.listChannels(pagination));
  }));

  return router;
}
