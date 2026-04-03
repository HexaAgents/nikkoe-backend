import { Router, Request, Response } from "express";
import type { SupplierService } from "../services/supplier.service.js";
import { asyncHandler } from "../middleware/asyncHandler.js";
import { paginationSchema } from "../schemas/index.js";

export function createSupplierRouter(service: SupplierService): Router {
  const router = Router();

  router.get("/", asyncHandler(async (req: Request, res: Response) => {
    const pagination = paginationSchema.parse(req.query);
    res.json(await service.listSuppliers(pagination));
  }));

  router.post("/", asyncHandler(async (req: Request, res: Response) => {
    const data = await service.createSupplier(req.body);
    res.status(201).json(data);
  }));

  router.delete("/:id", asyncHandler(async (req: Request, res: Response) => {
    await service.deleteSupplier(req.params.id);
    res.json({ success: true });
  }));

  return router;
}
