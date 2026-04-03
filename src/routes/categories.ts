import { Router, Request, Response } from "express";
import type { CategoryService } from "../services/category.service.js";
import { asyncHandler } from "../middleware/asyncHandler.js";
import { paginationSchema } from "../schemas/index.js";

export function createCategoryRouter(service: CategoryService): Router {
  const router = Router();

  router.get("/", asyncHandler(async (req: Request, res: Response) => {
    const pagination = paginationSchema.parse(req.query);
    res.json(await service.listCategories(pagination));
  }));

  router.post("/", asyncHandler(async (req: Request, res: Response) => {
    const data = await service.createCategory(req.body);
    res.status(201).json(data);
  }));

  router.delete("/:id", asyncHandler(async (req: Request, res: Response) => {
    await service.deleteCategory(req.params.id);
    res.json({ success: true });
  }));

  return router;
}
