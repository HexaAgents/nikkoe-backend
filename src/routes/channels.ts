import { Router, Request, Response, NextFunction } from "express";
import { supabase } from "../services/supabase.js";

const router = Router();

router.get("/", async (_req: Request, res: Response, next: NextFunction) => {
  try {
    const { data, error } = await supabase.from("channels").select("*").order("channel_name");
    if (error) throw error;
    res.json(data);
  } catch (err) { next(err); }
});

export default router;
