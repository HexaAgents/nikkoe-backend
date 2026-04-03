import { supabase } from "./infrastructure/supabase.js";

import { createReceiptRepository } from "./repositories/receipt.repository.js";
import { createReceiptService } from "./services/receipt.service.js";
import { createReceiptRouter } from "./routes/receipts.js";

import { createSaleRepository } from "./repositories/sale.repository.js";
import { createSaleService } from "./services/sale.service.js";
import { createSaleRouter } from "./routes/sales.js";

import { createItemRepository } from "./repositories/item.repository.js";
import { createItemService } from "./services/item.service.js";
import { createItemRouter } from "./routes/items.js";

import { createSupplierRepository } from "./repositories/supplier.repository.js";
import { createSupplierService } from "./services/supplier.service.js";
import { createSupplierRouter } from "./routes/suppliers.js";

import { createLocationRepository } from "./repositories/location.repository.js";
import { createLocationService } from "./services/location.service.js";
import { createLocationRouter } from "./routes/locations.js";

import { createCategoryRepository } from "./repositories/category.repository.js";
import { createCategoryService } from "./services/category.service.js";
import { createCategoryRouter } from "./routes/categories.js";

import { createChannelRepository } from "./repositories/channel.repository.js";
import { createChannelService } from "./services/channel.service.js";
import { createChannelRouter } from "./routes/channels.js";

import { createCustomerRepository } from "./repositories/customer.repository.js";
import { createCustomerService } from "./services/customer.service.js";
import { createCustomerRouter } from "./routes/customers.js";

import { createInventoryRepository } from "./repositories/inventory.repository.js";
import { createInventoryService } from "./services/inventory.service.js";
import { createInventoryRouter } from "./routes/inventory.js";

import { createUserRepository } from "./repositories/user.repository.js";
import { createUserService } from "./services/user.service.js";
import { createUserRouter } from "./routes/users.js";

import { createSupplierQuoteRepository } from "./repositories/supplierQuote.repository.js";
import { createSupplierQuoteService } from "./services/supplierQuote.service.js";
import { createSupplierQuoteRouter } from "./routes/supplierQuotes.js";

import { createAuthMiddleware } from "./middleware/auth.js";

// --- Repositories ---

const receiptRepo = createReceiptRepository(supabase);
const saleRepo = createSaleRepository(supabase);
const itemRepo = createItemRepository(supabase);
const supplierRepo = createSupplierRepository(supabase);
const locationRepo = createLocationRepository(supabase);
const categoryRepo = createCategoryRepository(supabase);
const channelRepo = createChannelRepository(supabase);
const customerRepo = createCustomerRepository(supabase);
const inventoryRepo = createInventoryRepository(supabase);
const userRepo = createUserRepository(supabase);
const supplierQuoteRepo = createSupplierQuoteRepository(supabase);

// --- Middleware ---

export const requireAuth = createAuthMiddleware(supabase);

// --- Routers ---

export const receiptRouter = createReceiptRouter(
  createReceiptService(receiptRepo),
);
export const saleRouter = createSaleRouter(
  createSaleService(saleRepo),
);
export const itemRouter = createItemRouter(
  createItemService(itemRepo, supplierQuoteRepo, inventoryRepo, receiptRepo, saleRepo),
);
export const supplierRouter = createSupplierRouter(
  createSupplierService(supplierRepo),
);
export const locationRouter = createLocationRouter(
  createLocationService(locationRepo),
);
export const categoryRouter = createCategoryRouter(
  createCategoryService(categoryRepo),
);
export const channelRouter = createChannelRouter(
  createChannelService(channelRepo),
);
export const customerRouter = createCustomerRouter(
  createCustomerService(customerRepo),
);
export const inventoryRouter = createInventoryRouter(
  createInventoryService(inventoryRepo),
);
export const userRouter = createUserRouter(
  createUserService(userRepo),
);
export const supplierQuoteRouter = createSupplierQuoteRouter(
  createSupplierQuoteService(supplierQuoteRepo),
);
