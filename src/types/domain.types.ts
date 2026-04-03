export interface Category {
  category_id: string;
  name: string;
}

export interface CategoryInput {
  name: string;
}

export interface Channel {
  channel_id: string;
  channel_name: string;
}

export interface Customer {
  customer_id: string;
  name: string;
}

export interface CustomerInput {
  name: string;
}

export interface InventoryMovement {
  movement_id: string;
  item_id: string | null;
  stock_id_from_id: string | null;
  stock_id_to_id: string | null;
  quantity: number;
  user_id: string | null;
  moved_at: string;
}

export interface InventoryMovementWithRelations extends InventoryMovement {
  items: { item_id: string; part_number: string } | null;
  users: { user_id: string; name: string } | null;
}

export interface InventoryBalance {
  item_id: string;
  location_id: string;
  quantity_on_hand: number;
}

export interface Item {
  item_id: string;
  part_number: string;
  description: string | null;
  category_id: string | null;
}

export interface ItemInput {
  part_number: string;
  description?: string;
  category_id?: string | null;
}

export interface ItemWithRelations extends Item {
  categories: { category_id: string; name: string } | null;
  inventory_balances: {
    quantity_on_hand: number;
    locations: { location_id: string; location_code: string } | null;
  }[];
  receipt_lines: {
    unit_cost: number;
    receipts: { receipt_id: string; status: string } | null;
  }[];
}

export interface Location {
  location_id: string;
  location_code: string;
}

export interface LocationInput {
  location_code: string;
}

export interface Receipt {
  receipt_id: string;
  supplier_id: string | null;
  reference: string | null;
  note: string | null;
  received_by: string | null;
  received_at: string;
  status: string;
}

export interface ReceiptLine {
  receipt_line_id: string;
  receipt_id: string;
  item_id: string;
  location_id: string;
  quantity: number;
  unit_cost: number;
  currency_code: string;
}

export interface ReceiptInput {
  supplier_id?: string;
  reference?: string;
  note?: string;
}

export interface ReceiptLineInput {
  item_id: string;
  location_id: string;
  quantity: number;
  unit_cost: number;
  currency_code: string;
}

export interface ReceiptWithRelations extends Receipt {
  suppliers: { supplier_id: string; supplier_name: string } | null;
  users: { user_id: string; name: string } | null;
}

export interface Sale {
  sale_id: string;
  customer_name: string | null;
  channel_id: string | null;
  note: string | null;
  sold_by: string | null;
  sold_at: string;
  status: string;
}

export interface SaleLine {
  sale_line_id: string;
  sale_id: string;
  item_id: string;
  location_id: string;
  quantity: number;
  unit_price: number;
  currency_code: string;
}

export interface SaleInput {
  customer_name?: string;
  channel_id?: string;
  note?: string;
}

export interface SaleLineInput {
  item_id: string;
  location_id: string;
  quantity: number;
  unit_price: number;
  currency_code: string;
}

export interface SaleWithRelations extends Sale {
  channels: { channel_id: string; channel_name: string } | null;
  users: { user_id: string; name: string } | null;
}

export interface Supplier {
  supplier_id: string;
  supplier_name: string;
  supplier_address: string | null;
  supplier_email: string | null;
  supplier_phone: string | null;
}

export interface SupplierInput {
  supplier_name: string;
  supplier_address?: string;
  supplier_email?: string;
  supplier_phone?: string;
}

export interface SupplierQuote {
  quote_id: string;
  item_id: string;
  supplier_id: string;
  unit_cost: number;
  currency: string;
  quoted_at: string | null;
  note: string | null;
}

export interface SupplierQuoteInput {
  item_id: string;
  supplier_id: string;
  unit_cost: number;
  currency: string;
  quoted_at?: string;
  note?: string;
}

export interface UserProfile {
  user_id: string;
  name: string;
  email_address: string | null;
  role: string | null;
}

export interface CreateUserInput {
  email: string;
  password: string;
}

export interface CreatedUser {
  id: string;
  email: string | undefined;
}
