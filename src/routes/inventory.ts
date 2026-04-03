import { Router, Request, Response } from "express";
import type { InventoryService } from "../services/inventory.service.js";
import { asyncHandler } from "../middleware/asyncHandler.js";
import { paginationSchema } from "../schemas/index.js";

export function createInventoryRouter(service: InventoryService): Router {
  const router = Router();

  router.get("/movements", asyncHandler(async (req: Request, res: Response) => {
    const pagination = paginationSchema.parse(req.query);
    res.json(await service.listMovements(pagination));
  }));

  router.get("/on-hand", asyncHandler(async (_req: Request, res: Response) => {
    res.json(await service.listOnHand());
  }));

  return router;
}
