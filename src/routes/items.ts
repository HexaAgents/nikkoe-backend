import { Router, Request, Response, NextFunction } from "express";
import { z } from "zod";
import { supabase } from "../services/supabase.js";

const router = Router();

const itemInputSchema = z.object({
  part_number: z.string().trim().min(1).max(255),
  description: z.string().max(1000).optional().or(z.literal("")),
  category_id: z.string().uuid().optional().or(z.literal("")).or(z.null()),
});

router.get("/", async (_req: Request, res: Response, next: NextFunction) => {
  try {
    const { data: items, error } = await supabase.from("items").select("*").order("part_number");
    if (error) throw error;
    if (!items || items.length === 0) { res.json([]); return; }

    const itemIds = items.map((i) => i.item_id);
    const categoryIds = [...new Set(items.map((i) => i.category_id).filter(Boolean))] as string[];

    const [categoriesResult, balancesResult, receiptLinesResult] = await Promise.all([
      categoryIds.length > 0
        ? supabase.from("categories").select("category_id, name").in("category_id", categoryIds)
        : { data: [], error: null },
      supabase.from("inventory_balances").select("item_id, quantity_on_hand, location_id").in("item_id", itemIds),
      supabase.from("receipt_lines").select("item_id, unit_cost, receipt_id").in("item_id", itemIds),
    ]);

    const locationIds = [...new Set((balancesResult.data || []).map((b) => b.location_id).filter(Boolean))] as string[];
    const receiptIds = [...new Set((receiptLinesResult.data || []).map((l) => l.receipt_id).filter(Boolean))] as string[];

    const [locationsResult, receiptsResult] = await Promise.all([
      locationIds.length > 0
        ? supabase.from("locations").select("location_id, location_code").in("location_id", locationIds)
        : { data: [], error: null },
      receiptIds.length > 0
        ? supabase.from("receipts").select("receipt_id, status").in("receipt_id", receiptIds)
        : { data: [], error: null },
    ]);

    const categoriesById = new Map((categoriesResult.data || []).map((c) => [c.category_id, c]));
    const locationsById = new Map((locationsResult.data || []).map((l) => [l.location_id, l]));
    const receiptsById = new Map((receiptsResult.data || []).map((r) => [r.receipt_id, r]));

    const balancesByItemId = new Map<string, unknown[]>();
    for (const b of balancesResult.data || []) {
      const arr = balancesByItemId.get(b.item_id) || [];
      arr.push({ quantity_on_hand: b.quantity_on_hand, locations: b.location_id ? locationsById.get(b.location_id) || null : null });
      balancesByItemId.set(b.item_id, arr);
    }

    const receiptLinesByItemId = new Map<string, unknown[]>();
    for (const l of receiptLinesResult.data || []) {
      const arr = receiptLinesByItemId.get(l.item_id) || [];
      arr.push({ unit_cost: l.unit_cost, receipts: l.receipt_id ? receiptsById.get(l.receipt_id) || null : null });
      receiptLinesByItemId.set(l.item_id, arr);
    }

    res.json(items.map((item) => ({
      ...item,
      categories: item.category_id ? categoriesById.get(item.category_id) || null : null,
      inventory_balances: balancesByItemId.get(item.item_id) || [],
      receipt_lines: receiptLinesByItemId.get(item.item_id) || [],
    })));
  } catch (err) { next(err); }
});

router.get("/:id", async (req: Request, res: Response, next: NextFunction) => {
  try {
    const { data, error } = await supabase
      .from("items")
      .select("*, categories(name)")
      .eq("item_id", req.params.id)
      .single();
    if (error) throw error;
    res.json(data);
  } catch (err) { next(err); }
});

router.get("/:id/quotes", async (req: Request, res: Response, next: NextFunction) => {
  try {
    const { data, error } = await supabase
      .from("supplier_quotes")
      .select("*, suppliers(supplier_name)")
      .eq("item_id", req.params.id)
      .order("quoted_at", { ascending: false });
    if (error) throw error;
    res.json(data);
  } catch (err) { next(err); }
});

router.get("/:id/inventory", async (req: Request, res: Response, next: NextFunction) => {
  try {
    const { data, error } = await supabase
      .from("inventory_balances")
      .select("*, locations(location_code)")
      .eq("item_id", req.params.id);
    if (error) throw error;
    res.json(data);
  } catch (err) { next(err); }
});

router.get("/:id/receipts", async (req: Request, res: Response, next: NextFunction) => {
  try {
    const { data, error } = await supabase
      .from("receipt_lines")
      .select("*, receipts(receipt_id, received_at, suppliers(supplier_name)), locations(location_code)")
      .eq("item_id", req.params.id)
      .order("created_at", { ascending: false });
    if (error) throw error;
    res.json(data);
  } catch (err) { next(err); }
});

router.get("/:id/sales", async (req: Request, res: Response, next: NextFunction) => {
  try {
    const { data, error } = await supabase
      .from("sale_lines")
      .select("*, sales(sale_id, sold_at), locations(location_code)")
      .eq("item_id", req.params.id)
      .order("created_at", { ascending: false });
    if (error) throw error;
    res.json(data);
  } catch (err) { next(err); }
});

router.post("/", async (req: Request, res: Response, next: NextFunction) => {
  try {
    const validated = itemInputSchema.parse(req.body);
    const { data, error } = await supabase.from("items").insert(validated).select().single();
    if (error) throw error;
    res.status(201).json(data);
  } catch (err) { next(err); }
});

router.put("/:id", async (req: Request, res: Response, next: NextFunction) => {
  try {
    const validated = itemInputSchema.partial().parse(req.body);
    const { data, error } = await supabase.from("items").update(validated).eq("item_id", req.params.id).select().single();
    if (error) throw error;
    res.json(data);
  } catch (err) { next(err); }
});

router.delete("/:id", async (req: Request, res: Response, next: NextFunction) => {
  try {
    const { error } = await supabase.from("items").delete().eq("item_id", req.params.id);
    if (error) throw error;
    res.json({ success: true });
  } catch (err) { next(err); }
});

export default router;
