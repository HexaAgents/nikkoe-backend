import { Request, Response, NextFunction } from "express";
import { supabase } from "../services/supabase.js";

export async function requireAuth(req: Request, res: Response, next: NextFunction) {
  const token = req.headers.authorization?.replace("Bearer ", "");
  if (!token) {
    res.status(401).json({ error: "Missing authorization token" });
    return;
  }

  const { data: { user }, error } = await supabase.auth.getUser(token);
  if (error || !user) {
    res.status(401).json({ error: "Invalid or expired token" });
    return;
  }

  const { data: profile } = await supabase
    .from("users")
    .select("user_id, name, email_address, role")
    .eq("auth_id", user.id)
    .maybeSingle();

  req.user = { id: user.id, email: user.email, profile };
  next();
}
