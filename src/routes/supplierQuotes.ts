import { Router, Request, Response, NextFunction } from "express";
import { z } from "zod";
import { supabase } from "../services/supabase.js";

const router = Router();

const quoteInputSchema = z.object({
  item_id: z.string().uuid(),
  supplier_id: z.string().uuid(),
  unit_cost: z.number().nonnegative(),
  currency: z.string().min(1).max(10),
  quoted_at: z.string().datetime().optional(),
  note: z.string().max(500).optional().or(z.literal("")),
});

router.post("/", async (req: Request, res: Response, next: NextFunction) => {
  try {
    const validated = quoteInputSchema.parse(req.body);
    const { data, error } = await supabase.from("supplier_quotes").insert(validated).select().single();
    if (error) throw error;
    res.status(201).json(data);
  } catch (err) { next(err); }
});

router.delete("/:id", async (req: Request, res: Response, next: NextFunction) => {
  try {
    const { error } = await supabase.from("supplier_quotes").delete().eq("quote_id", req.params.id);
    if (error) throw error;
    res.json({ success: true });
  } catch (err) { next(err); }
});

export default router;
