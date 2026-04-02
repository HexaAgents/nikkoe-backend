import { Router, Request, Response, NextFunction } from "express";
import { z } from "zod";
import { supabase } from "../services/supabase.js";

const router = Router();

const saleInputSchema = z.object({
  customer_name: z.string().max(255).optional().or(z.literal("")),
  channel_id: z.string().uuid().optional().or(z.literal("")),
  note: z.string().max(1000).optional().or(z.literal("")),
});

const saleLineSchema = z.object({
  item_id: z.string().uuid("Item is required"),
  location_id: z.string().uuid("Location is required"),
  quantity: z.number().int().positive("Quantity must be > 0"),
  unit_price: z.number().nonnegative("Unit price cannot be negative"),
  currency_code: z.string().min(1).max(10),
});

router.get("/", async (_req: Request, res: Response, next: NextFunction) => {
  try {
    const { data: sales, error } = await supabase
      .from("sales")
      .select("*")
      .order("sold_at", { ascending: false });

    if (error) throw error;
    if (!sales || sales.length === 0) { res.json([]); return; }

    const channelIds = [...new Set(sales.map((s) => s.channel_id).filter(Boolean))] as string[];
    const userIds = [...new Set(sales.map((s) => s.sold_by).filter(Boolean))] as string[];

    const [channelsResult, usersResult] = await Promise.all([
      channelIds.length > 0
        ? supabase.from("channels").select("channel_id, channel_name").in("channel_id", channelIds)
        : { data: [], error: null },
      userIds.length > 0
        ? supabase.from("users").select("user_id, name").in("user_id", userIds)
        : { data: [], error: null },
    ]);

    const channelsById = new Map((channelsResult.data || []).map((c) => [c.channel_id, c]));
    const usersById = new Map((usersResult.data || []).map((u) => [u.user_id, u]));

    res.json(sales.map((s) => ({
      ...s,
      channels: s.channel_id ? channelsById.get(s.channel_id) || null : null,
      users: s.sold_by ? usersById.get(s.sold_by) || null : null,
    })));
  } catch (err) { next(err); }
});

router.get("/:id", async (req: Request, res: Response, next: NextFunction) => {
  try {
    const { data, error } = await supabase
      .from("sales")
      .select("*, channels(channel_name), users(name)")
      .eq("sale_id", req.params.id)
      .single();

    if (error) throw error;
    res.json(data);
  } catch (err) { next(err); }
});

router.get("/:id/lines", async (req: Request, res: Response, next: NextFunction) => {
  try {
    const { data, error } = await supabase
      .from("sale_lines")
      .select("*, items(part_number), locations(location_code)")
      .eq("sale_id", req.params.id)
      .order("created_at");

    if (error) throw error;
    res.json(data);
  } catch (err) { next(err); }
});

router.post("/", async (req: Request, res: Response, next: NextFunction) => {
  try {
    const { sale, lines } = req.body;
    const validated = saleInputSchema.parse(sale);
    const validatedLines = z.array(saleLineSchema).parse(lines);

    const saleInsert: Record<string, unknown> = { sale_id: crypto.randomUUID() };
    if (validated.customer_name) saleInsert.customer_name = validated.customer_name;
    if (validated.channel_id) saleInsert.channel_id = validated.channel_id;
    if (validated.note) saleInsert.note = validated.note;

    const { data: saleData, error: saleError } = await supabase
      .from("sales")
      .insert(saleInsert)
      .select()
      .single();

    if (saleError) throw saleError;

    if (validatedLines.length > 0) {
      const linesPayload = validatedLines.map((line) => ({
        sale_line_id: crypto.randomUUID(),
        sale_id: saleData.sale_id,
        item_id: line.item_id,
        location_id: line.location_id,
        quantity: line.quantity,
        unit_price: line.unit_price,
        currency_code: line.currency_code,
      }));

      const { error: linesError } = await supabase.from("sale_lines").insert(linesPayload);
      if (linesError) throw linesError;
    }

    res.status(201).json(saleData);
  } catch (err) { next(err); }
});

router.post("/:id/void", async (req: Request, res: Response, next: NextFunction) => {
  try {
    const userId = req.user?.profile?.user_id;
    const { reason } = req.body;

    const { error } = await supabase.rpc("void_sale", {
      p_sale_id: req.params.id,
      p_voided_by: userId,
      p_reason: reason || null,
    });

    if (error) throw error;
    res.json({ success: true });
  } catch (err) { next(err); }
});

export default router;
