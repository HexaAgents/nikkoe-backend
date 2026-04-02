import { Router, Request, Response, NextFunction } from "express";
import { z } from "zod";
import { supabase } from "../services/supabase.js";

const router = Router();

router.get("/", async (_req: Request, res: Response, next: NextFunction) => {
  try {
    const { data, error } = await supabase.from("customer").select("customer_id, name").order("name");
    if (error) throw error;
    res.json(data);
  } catch (err) { next(err); }
});

router.post("/", async (req: Request, res: Response, next: NextFunction) => {
  try {
    const name = z.string().trim().min(1).max(255).parse(req.body.name);
    const { data, error } = await supabase
      .from("customer")
      .insert({ customer_id: crypto.randomUUID(), name })
      .select("customer_id, name")
      .single();
    if (error) throw error;
    res.status(201).json(data);
  } catch (err) { next(err); }
});

export default router;
