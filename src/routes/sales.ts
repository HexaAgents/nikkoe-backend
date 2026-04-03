import { Router, Request, Response } from "express";
import type { SaleService } from "../services/sale.service.js";
import { asyncHandler } from "../middleware/asyncHandler.js";
import { ForbiddenError } from "../errors/index.js";
import { paginationSchema } from "../schemas/index.js";

export function createSaleRouter(service: SaleService): Router {
  const router = Router();

  router.get("/", asyncHandler(async (req: Request, res: Response) => {
    const pagination = paginationSchema.parse(req.query);
    res.json(await service.listSales(pagination));
  }));

  router.get("/:id", asyncHandler(async (req: Request, res: Response) => {
    res.json(await service.getSale(req.params.id));
  }));

  router.get("/:id/lines", asyncHandler(async (req: Request, res: Response) => {
    res.json(await service.getSaleLines(req.params.id));
  }));

  router.post("/", asyncHandler(async (req: Request, res: Response) => {
    const data = await service.createSale(req.body);
    res.status(201).json(data);
  }));

  router.post("/:id/void", asyncHandler(async (req: Request, res: Response) => {
    const userId = req.user?.profile?.user_id;
    if (!userId) throw new ForbiddenError("User profile required to void");
    await service.voidSale(req.params.id, userId, req.body.reason);
    res.json({ success: true });
  }));

  return router;
}
