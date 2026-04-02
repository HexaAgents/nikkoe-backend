import { Router, Request, Response, NextFunction } from "express";
import { z } from "zod";
import { supabase } from "../services/supabase.js";

const router = Router();

const receiptInputSchema = z.object({
  supplier_id: z.string().uuid().optional().or(z.literal("")),
  reference: z.string().max(255).optional().or(z.literal("")),
  note: z.string().max(1000).optional().or(z.literal("")),
});

const receiptLineSchema = z.object({
  item_id: z.string().uuid("Item is required"),
  location_id: z.string().uuid("Location is required"),
  quantity: z.number().int().positive("Quantity must be > 0"),
  unit_cost: z.number().nonnegative("Unit cost cannot be negative"),
  currency_code: z.string().min(1).max(10),
});

router.get("/", async (_req: Request, res: Response, next: NextFunction) => {
  try {
    const { data: receipts, error } = await supabase
      .from("receipts")
      .select("*")
      .order("received_at", { ascending: false });

    if (error) throw error;
    if (!receipts || receipts.length === 0) { res.json([]); return; }

    const supplierIds = [...new Set(receipts.map((r) => r.supplier_id).filter(Boolean))] as string[];
    const userIds = [...new Set(receipts.map((r) => r.received_by).filter(Boolean))] as string[];

    const [suppliersResult, usersResult] = await Promise.all([
      supplierIds.length > 0
        ? supabase.from("suppliers").select("supplier_id, supplier_name").in("supplier_id", supplierIds)
        : { data: [], error: null },
      userIds.length > 0
        ? supabase.from("users").select("user_id, name").in("user_id", userIds)
        : { data: [], error: null },
    ]);

    const suppliersById = new Map((suppliersResult.data || []).map((s) => [s.supplier_id, s]));
    const usersById = new Map((usersResult.data || []).map((u) => [u.user_id, u]));

    res.json(receipts.map((r) => ({
      ...r,
      suppliers: r.supplier_id ? suppliersById.get(r.supplier_id) || null : null,
      users: r.received_by ? usersById.get(r.received_by) || null : null,
    })));
  } catch (err) { next(err); }
});

router.get("/:id", async (req: Request, res: Response, next: NextFunction) => {
  try {
    const { data: receipt, error } = await supabase
      .from("receipts")
      .select("*")
      .eq("receipt_id", req.params.id)
      .single();

    if (error) throw error;

    const [suppliersResult, usersResult] = await Promise.all([
      receipt.supplier_id
        ? supabase.from("suppliers").select("supplier_id, supplier_name").eq("supplier_id", receipt.supplier_id).maybeSingle()
        : { data: null, error: null },
      receipt.received_by
        ? supabase.from("users").select("user_id, name").eq("user_id", receipt.received_by).maybeSingle()
        : { data: null, error: null },
    ]);

    res.json({ ...receipt, suppliers: suppliersResult.data, users: usersResult.data });
  } catch (err) { next(err); }
});

router.get("/:id/lines", async (req: Request, res: Response, next: NextFunction) => {
  try {
    const { data, error } = await supabase
      .from("receipt_lines")
      .select("*")
      .eq("receipt_id", req.params.id)
      .order("created_at");

    if (error) throw error;
    res.json(data);
  } catch (err) { next(err); }
});

router.post("/", async (req: Request, res: Response, next: NextFunction) => {
  try {
    const { receipt, lines } = req.body;
    const validated = receiptInputSchema.parse(receipt);
    const validatedLines = z.array(receiptLineSchema).parse(lines);

    const receiptInsert: Record<string, unknown> = {};
    if (validated.supplier_id) receiptInsert.supplier_id = validated.supplier_id;
    if (validated.reference) receiptInsert.reference = validated.reference;
    if (validated.note) receiptInsert.note = validated.note;

    const { data: receiptData, error: receiptError } = await supabase
      .from("receipts")
      .insert(receiptInsert)
      .select()
      .single();

    if (receiptError) throw receiptError;

    if (validatedLines.length > 0) {
      const linesPayload = validatedLines.map((line) => ({
        receipt_line_id: crypto.randomUUID(),
        receipt_id: receiptData.receipt_id,
        item_id: line.item_id,
        location_id: line.location_id,
        quantity: line.quantity,
        unit_cost: line.unit_cost,
        currency_code: line.currency_code,
      }));

      const { error: linesError } = await supabase.from("receipt_lines").insert(linesPayload);
      if (linesError) throw linesError;
    }

    res.status(201).json(receiptData);
  } catch (err) { next(err); }
});

router.post("/:id/void", async (req: Request, res: Response, next: NextFunction) => {
  try {
    const userId = req.user?.profile?.user_id;
    const { reason } = req.body;

    const { error } = await supabase.rpc("void_receipt", {
      p_receipt_id: req.params.id,
      p_voided_by: userId,
      p_reason: reason || null,
    });

    if (error) throw error;
    res.json({ success: true });
  } catch (err) { next(err); }
});

export default router;
