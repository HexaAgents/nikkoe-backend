import { Router, Request, Response } from "express";
import type { UserService } from "../services/user.service.js";
import { asyncHandler } from "../middleware/asyncHandler.js";

export function createUserRouter(service: UserService): Router {
  const router = Router();

  router.get("/me", asyncHandler(async (req: Request, res: Response) => {
    res.json(service.getProfile(req.user?.profile));
  }));

  router.post("/", asyncHandler(async (req: Request, res: Response) => {
    const user = await service.createUser(req.body);
    res.status(201).json({ user });
  }));

  return router;
}
