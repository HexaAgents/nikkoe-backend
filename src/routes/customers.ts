import { Router, Request, Response } from "express";
import type { CustomerService } from "../services/customer.service.js";
import { asyncHandler } from "../middleware/asyncHandler.js";
import { paginationSchema } from "../schemas/index.js";

export function createCustomerRouter(service: CustomerService): Router {
  const router = Router();

  router.get("/", asyncHandler(async (req: Request, res: Response) => {
    const pagination = paginationSchema.parse(req.query);
    res.json(await service.listCustomers(pagination));
  }));

  router.post("/", asyncHandler(async (req: Request, res: Response) => {
    const data = await service.createCustomer(req.body);
    res.status(201).json(data);
  }));

  return router;
}
