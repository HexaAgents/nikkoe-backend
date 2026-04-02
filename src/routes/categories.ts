import { Router, Request, Response, NextFunction } from "express";
import { z } from "zod";
import { supabase } from "../services/supabase.js";

const router = Router();

router.get("/", async (_req: Request, res: Response, next: NextFunction) => {
  try {
    const { data, error } = await supabase.from("categories").select("*").order("name");
    if (error) throw error;
    res.json(data);
  } catch (err) { next(err); }
});

router.post("/", async (req: Request, res: Response, next: NextFunction) => {
  try {
    const name = z.string().trim().min(1).max(255).parse(req.body.name);
    const { data, error } = await supabase.from("categories").insert({ name }).select().single();
    if (error) throw error;
    res.status(201).json(data);
  } catch (err) { next(err); }
});

router.delete("/:id", async (req: Request, res: Response, next: NextFunction) => {
  try {
    const { error } = await supabase.from("categories").delete().eq("category_id", req.params.id);
    if (error) throw error;
    res.json({ success: true });
  } catch (err) { next(err); }
});

export default router;
