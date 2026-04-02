import { Router, Request, Response, NextFunction } from "express";
import { supabase } from "../services/supabase.js";

const router = Router();

router.get("/movements", async (_req: Request, res: Response, next: NextFunction) => {
  try {
    const { data: movements, error } = await supabase
      .from("inventory_movements")
      .select("*")
      .order("moved_at", { ascending: false });

    if (error) throw error;
    if (!movements || movements.length === 0) { res.json([]); return; }

    const itemIds = [...new Set(movements.map((m) => m.item_id).filter(Boolean))] as string[];
    const locationIds = [...new Set(
      movements.flatMap((m) => [m.stock_id_from_id, m.stock_id_to_id]).filter(Boolean)
    )] as string[];
    const userIds = [...new Set(movements.map((m) => m.user_id).filter(Boolean))] as string[];

    const [itemsResult, usersResult] = await Promise.all([
      itemIds.length > 0
        ? supabase.from("items").select("item_id, part_number").in("item_id", itemIds)
        : { data: [], error: null },
      userIds.length > 0
        ? supabase.from("users").select("user_id, name").in("user_id", userIds)
        : { data: [], error: null },
    ]);

    const itemsById = new Map((itemsResult.data || []).map((i) => [i.item_id, i]));
    const usersById = new Map((usersResult.data || []).map((u) => [u.user_id, u]));

    res.json(movements.map((m) => ({
      ...m,
      items: m.item_id ? itemsById.get(m.item_id) || null : null,
      users: m.user_id ? usersById.get(m.user_id) || null : null,
    })));
  } catch (err) { next(err); }
});

router.get("/on-hand", async (_req: Request, res: Response, next: NextFunction) => {
  try {
    const { data, error } = await supabase
      .from("inventory_balances")
      .select("*")
      .gt("quantity_on_hand", 0);
    if (error) throw error;
    res.json(data);
  } catch (err) { next(err); }
});

export default router;
