import { Router, Request, Response, NextFunction } from "express";
import { z } from "zod";
import { supabase } from "../services/supabase.js";

const router = Router();

router.get("/me", async (req: Request, res: Response) => {
  if (!req.user?.profile) {
    res.status(404).json({ error: "User profile not found" });
    return;
  }
  res.json(req.user.profile);
});

router.post("/", async (req: Request, res: Response, next: NextFunction) => {
  try {
    const schema = z.object({
      email: z.string().email(),
      password: z.string().min(6, "Password must be at least 6 characters"),
    });
    const { email, password } = schema.parse(req.body);

    const { data, error } = await supabase.auth.admin.createUser({
      email,
      password,
      email_confirm: true,
    });

    if (error) {
      res.status(400).json({ error: error.message });
      return;
    }

    res.status(201).json({ user: { id: data.user.id, email: data.user.email } });
  } catch (err) { next(err); }
});

export default router;
