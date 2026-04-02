import { Router, Request, Response, NextFunction } from "express";
import { z } from "zod";
import { supabase } from "../services/supabase.js";

const router = Router();

const supplierInputSchema = z.object({
  supplier_name: z.string().trim().min(1).max(255),
  supplier_address: z.string().max(500).optional().or(z.literal("")),
  supplier_email: z.string().email().max(255).optional().or(z.literal("")),
  supplier_phone: z.string().max(20).optional().or(z.literal("")),
});

router.get("/", async (_req: Request, res: Response, next: NextFunction) => {
  try {
    const { data, error } = await supabase.from("suppliers").select("*").order("supplier_name");
    if (error) throw error;
    res.json(data);
  } catch (err) { next(err); }
});

router.post("/", async (req: Request, res: Response, next: NextFunction) => {
  try {
    const validated = supplierInputSchema.parse(req.body);
    const { data, error } = await supabase.from("suppliers").insert(validated).select().single();
    if (error) throw error;
    res.status(201).json(data);
  } catch (err) { next(err); }
});

router.delete("/:id", async (req: Request, res: Response, next: NextFunction) => {
  try {
    const { error } = await supabase.from("suppliers").delete().eq("supplier_id", req.params.id);
    if (error) throw error;
    res.json({ success: true });
  } catch (err) { next(err); }
});

export default router;
