import { Router, Request, Response } from "express";
import type { SupplierQuoteService } from "../services/supplierQuote.service.js";
import { asyncHandler } from "../middleware/asyncHandler.js";

export function createSupplierQuoteRouter(
  service: SupplierQuoteService,
): Router {
  const router = Router();

  router.post("/", asyncHandler(async (req: Request, res: Response) => {
    const data = await service.createQuote(req.body);
    res.status(201).json(data);
  }));

  router.delete("/:id", asyncHandler(async (req: Request, res: Response) => {
    await service.deleteQuote(req.params.id);
    res.json({ success: true });
  }));

  return router;
}
