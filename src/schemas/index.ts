import { z } from "zod";

export const optionalUuid = z.string().uuid().optional().or(z.literal(""));
export const currencyCode = z.string().min(1).max(10);
export const optionalNote = z.string().max(1000).optional().or(z.literal(""));

export const paginationSchema = z.object({
  limit: z.coerce.number().int().min(1).max(100).default(50),
  offset: z.coerce.number().int().min(0).default(0),
});

export const categoryInputSchema = z.object({
  name: z.string().trim().min(1).max(255),
});

export const customerInputSchema = z.object({
  name: z.string().trim().min(1).max(255),
});

export const itemInputSchema = z.object({
  part_number: z.string().trim().min(1).max(255),
  description: z.string().max(1000).optional().or(z.literal("")),
  category_id: optionalUuid.or(z.null()),
});

export const locationInputSchema = z.object({
  location_code: z.string().trim().min(1).max(50),
});

export const receiptInputSchema = z.object({
  supplier_id: optionalUuid,
  reference: z.string().max(255).optional().or(z.literal("")),
  note: optionalNote,
});

export const receiptLineSchema = z.object({
  item_id: z.string().uuid("Item is required"),
  location_id: z.string().uuid("Location is required"),
  quantity: z.number().int().positive("Quantity must be > 0"),
  unit_cost: z.number().nonnegative("Unit cost cannot be negative"),
  currency_code: currencyCode,
});

export const saleInputSchema = z.object({
  customer_name: z.string().max(255).optional().or(z.literal("")),
  channel_id: optionalUuid,
  note: optionalNote,
});

export const saleLineSchema = z.object({
  item_id: z.string().uuid("Item is required"),
  location_id: z.string().uuid("Location is required"),
  quantity: z.number().int().positive("Quantity must be > 0"),
  unit_price: z.number().nonnegative("Unit price cannot be negative"),
  currency_code: currencyCode,
});

export const supplierInputSchema = z.object({
  supplier_name: z.string().trim().min(1).max(255),
  supplier_address: z.string().max(500).optional().or(z.literal("")),
  supplier_email: z.string().email().max(255).optional().or(z.literal("")),
  supplier_phone: z.string().max(20).optional().or(z.literal("")),
});

export const quoteInputSchema = z.object({
  item_id: z.string().uuid(),
  supplier_id: z.string().uuid(),
  unit_cost: z.number().nonnegative(),
  currency: z.string().min(1).max(10),
  quoted_at: z.string().datetime().optional(),
  note: z.string().max(500).optional().or(z.literal("")),
});

export const createUserSchema = z.object({
  email: z.string().email(),
  password: z.string().min(6, "Password must be at least 6 characters"),
});
