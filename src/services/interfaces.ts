import type {
  Category,
  Channel,
  Customer,
  InventoryMovementWithRelations,
  InventoryBalance,
  Item,
  ItemWithRelations,
  Location,
  Receipt,
  ReceiptLine,
  ReceiptWithRelations,
  Sale,
  SaleLine,
  SaleWithRelations,
  Supplier,
  SupplierQuote,
  UserProfile,
  CreatedUser,
} from "../types/domain.types.js";
import type { PaginationParams, PaginatedResult } from "../types/pagination.types.js";

export interface ICategoryService {
  listCategories(pagination?: PaginationParams): Promise<PaginatedResult<Category>>;
  createCategory(body: unknown): Promise<Category>;
  deleteCategory(id: string): Promise<void>;
}

export interface IChannelService {
  listChannels(pagination?: PaginationParams): Promise<PaginatedResult<Channel>>;
}

export interface ICustomerService {
  listCustomers(pagination?: PaginationParams): Promise<PaginatedResult<Customer>>;
  createCustomer(body: unknown): Promise<Customer>;
}

export interface IInventoryService {
  listMovements(pagination?: PaginationParams): Promise<PaginatedResult<InventoryMovementWithRelations>>;
  listOnHand(): Promise<InventoryBalance[]>;
}

export interface IItemService {
  listItems(pagination?: PaginationParams): Promise<PaginatedResult<ItemWithRelations>>;
  getItem(id: string): Promise<Item>;
  getItemQuotes(itemId: string): Promise<unknown[]>;
  getItemInventory(itemId: string): Promise<unknown[]>;
  getItemReceipts(itemId: string): Promise<unknown[]>;
  getItemSales(itemId: string): Promise<unknown[]>;
  createItem(body: unknown): Promise<Item>;
  updateItem(id: string, body: unknown): Promise<Item>;
  deleteItem(id: string): Promise<void>;
}

export interface ILocationService {
  listLocations(pagination?: PaginationParams): Promise<PaginatedResult<Location>>;
  createLocation(body: unknown): Promise<Location>;
  deleteLocation(id: string): Promise<void>;
}

export interface IReceiptService {
  listReceipts(pagination?: PaginationParams): Promise<PaginatedResult<ReceiptWithRelations>>;
  getReceipt(id: string): Promise<ReceiptWithRelations>;
  getReceiptLines(receiptId: string): Promise<ReceiptLine[]>;
  createReceipt(body: { receipt: unknown; lines: unknown }): Promise<Receipt>;
  voidReceipt(receiptId: string, userId: string, reason?: string): Promise<void>;
}

export interface ISaleService {
  listSales(pagination?: PaginationParams): Promise<PaginatedResult<SaleWithRelations>>;
  getSale(id: string): Promise<SaleWithRelations>;
  getSaleLines(saleId: string): Promise<SaleLine[]>;
  createSale(body: { sale: unknown; lines: unknown }): Promise<Sale>;
  voidSale(saleId: string, userId: string, reason?: string): Promise<void>;
}

export interface ISupplierService {
  listSuppliers(pagination?: PaginationParams): Promise<PaginatedResult<Supplier>>;
  createSupplier(body: unknown): Promise<Supplier>;
  deleteSupplier(id: string): Promise<void>;
}

export interface ISupplierQuoteService {
  createQuote(body: unknown): Promise<SupplierQuote>;
  deleteQuote(id: string): Promise<void>;
}

export interface IUserService {
  getProfile(profile: UserProfile | null | undefined): UserProfile;
  createUser(body: unknown): Promise<CreatedUser>;
}
