import { Router, Request, Response } from "express";
import type { LocationService } from "../services/location.service.js";
import { asyncHandler } from "../middleware/asyncHandler.js";
import { paginationSchema } from "../schemas/index.js";

export function createLocationRouter(service: LocationService): Router {
  const router = Router();

  router.get("/", asyncHandler(async (req: Request, res: Response) => {
    const pagination = paginationSchema.parse(req.query);
    res.json(await service.listLocations(pagination));
  }));

  router.post("/", asyncHandler(async (req: Request, res: Response) => {
    const data = await service.createLocation(req.body);
    res.status(201).json(data);
  }));

  router.delete("/:id", asyncHandler(async (req: Request, res: Response) => {
    await service.deleteLocation(req.params.id);
    res.json({ success: true });
  }));

  return router;
}
