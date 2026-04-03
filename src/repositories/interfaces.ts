import type {
  Category,
  CategoryInput,
  Channel,
  Customer,
  CustomerInput,
  InventoryMovementWithRelations,
  InventoryBalance,
  Item,
  ItemInput,
  ItemWithRelations,
  Location,
  LocationInput,
  Receipt,
  ReceiptLine,
  ReceiptWithRelations,
  ReceiptInput,
  ReceiptLineInput,
  Sale,
  SaleLine,
  SaleWithRelations,
  SaleInput,
  SaleLineInput,
  Supplier,
  SupplierInput,
  SupplierQuote,
  SupplierQuoteInput,
  CreatedUser,
  CreateUserInput,
} from "../types/domain.types.js";
import type { PaginationParams, PaginatedResult } from "../types/pagination.types.js";

export interface ICategoryRepository {
  findAll(pagination?: PaginationParams): Promise<PaginatedResult<Category>>;
  create(input: CategoryInput): Promise<Category>;
  remove(id: string): Promise<void>;
}

export interface IChannelRepository {
  findAll(pagination?: PaginationParams): Promise<PaginatedResult<Channel>>;
}

export interface ICustomerRepository {
  findAll(pagination?: PaginationParams): Promise<PaginatedResult<Customer>>;
  create(input: CustomerInput): Promise<Customer>;
}

export interface IInventoryRepository {
  findMovements(pagination?: PaginationParams): Promise<PaginatedResult<InventoryMovementWithRelations>>;
  findOnHand(): Promise<InventoryBalance[]>;
  findByItemId(itemId: string): Promise<unknown[]>;
}

export interface IItemRepository {
  findAll(pagination?: PaginationParams): Promise<PaginatedResult<ItemWithRelations>>;
  findById(id: string): Promise<Item | null>;
  create(input: ItemInput): Promise<Item>;
  update(id: string, input: Partial<ItemInput>): Promise<Item>;
  remove(id: string): Promise<void>;
}

export interface ILocationRepository {
  findAll(pagination?: PaginationParams): Promise<PaginatedResult<Location>>;
  create(input: LocationInput): Promise<Location>;
  remove(id: string): Promise<void>;
}

export interface IReceiptRepository {
  findAll(pagination?: PaginationParams): Promise<PaginatedResult<ReceiptWithRelations>>;
  findById(id: string): Promise<ReceiptWithRelations | null>;
  findLines(receiptId: string): Promise<ReceiptLine[]>;
  findByItemId(itemId: string): Promise<unknown[]>;
  create(receipt: ReceiptInput, lines: ReceiptLineInput[]): Promise<Receipt>;
  voidReceipt(receiptId: string, userId: string, reason?: string): Promise<void>;
}

export interface ISaleRepository {
  findAll(pagination?: PaginationParams): Promise<PaginatedResult<SaleWithRelations>>;
  findById(id: string): Promise<SaleWithRelations | null>;
  findLines(saleId: string): Promise<SaleLine[]>;
  findByItemId(itemId: string): Promise<unknown[]>;
  create(sale: SaleInput, lines: SaleLineInput[]): Promise<Sale>;
  voidSale(saleId: string, userId: string, reason?: string): Promise<void>;
}

export interface ISupplierRepository {
  findAll(pagination?: PaginationParams): Promise<PaginatedResult<Supplier>>;
  create(input: SupplierInput): Promise<Supplier>;
  remove(id: string): Promise<void>;
}

export interface ISupplierQuoteRepository {
  findByItemId(itemId: string): Promise<unknown[]>;
  create(input: SupplierQuoteInput): Promise<SupplierQuote>;
  remove(id: string): Promise<void>;
}

export interface IUserRepository {
  createAuthUser(input: CreateUserInput): Promise<CreatedUser>;
}
