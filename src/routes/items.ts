import { Router, Request, Response } from "express";
import type { ItemService } from "../services/item.service.js";
import { asyncHandler } from "../middleware/asyncHandler.js";
import { paginationSchema } from "../schemas/index.js";

export function createItemRouter(service: ItemService): Router {
  const router = Router();

  router.get("/", asyncHandler(async (req: Request, res: Response) => {
    const pagination = paginationSchema.parse(req.query);
    res.json(await service.listItems(pagination));
  }));

  router.get("/:id", asyncHandler(async (req: Request, res: Response) => {
    res.json(await service.getItem(req.params.id));
  }));

  router.get("/:id/quotes", asyncHandler(async (req: Request, res: Response) => {
    res.json(await service.getItemQuotes(req.params.id));
  }));

  router.get("/:id/inventory", asyncHandler(async (req: Request, res: Response) => {
    res.json(await service.getItemInventory(req.params.id));
  }));

  router.get("/:id/receipts", asyncHandler(async (req: Request, res: Response) => {
    res.json(await service.getItemReceipts(req.params.id));
  }));

  router.get("/:id/sales", asyncHandler(async (req: Request, res: Response) => {
    res.json(await service.getItemSales(req.params.id));
  }));

  router.post("/", asyncHandler(async (req: Request, res: Response) => {
    const data = await service.createItem(req.body);
    res.status(201).json(data);
  }));

  router.put("/:id", asyncHandler(async (req: Request, res: Response) => {
    res.json(await service.updateItem(req.params.id, req.body));
  }));

  router.delete("/:id", asyncHandler(async (req: Request, res: Response) => {
    await service.deleteItem(req.params.id);
    res.json({ success: true });
  }));

  return router;
}
