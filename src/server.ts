import express from "express";
import cors from "cors";
import { requireAuth } from "./middleware/auth.js";
import { errorHandler } from "./middleware/errorHandler.js";
import receiptsRouter from "./routes/receipts.js";
import salesRouter from "./routes/sales.js";
import itemsRouter from "./routes/items.js";
import suppliersRouter from "./routes/suppliers.js";
import locationsRouter from "./routes/locations.js";
import categoriesRouter from "./routes/categories.js";
import channelsRouter from "./routes/channels.js";
import customersRouter from "./routes/customers.js";
import inventoryRouter from "./routes/inventory.js";
import usersRouter from "./routes/users.js";
import supplierQuotesRouter from "./routes/supplierQuotes.js";

const app = express();
const port = parseInt(process.env.PORT || "3000", 10);

app.use(cors({ origin: process.env.CORS_ORIGIN || "http://localhost:8080", credentials: true }));
app.use(express.json());

app.get("/api/health", (_req, res) => {
  res.json({ status: "ok", timestamp: new Date().toISOString() });
});

app.use("/api/receipts", requireAuth, receiptsRouter);
app.use("/api/sales", requireAuth, salesRouter);
app.use("/api/items", requireAuth, itemsRouter);
app.use("/api/suppliers", requireAuth, suppliersRouter);
app.use("/api/locations", requireAuth, locationsRouter);
app.use("/api/categories", requireAuth, categoriesRouter);
app.use("/api/channels", requireAuth, channelsRouter);
app.use("/api/customers", requireAuth, customersRouter);
app.use("/api/inventory", requireAuth, inventoryRouter);
app.use("/api/users", requireAuth, usersRouter);
app.use("/api/supplier-quotes", requireAuth, supplierQuotesRouter);

app.use(errorHandler);

app.listen(port, () => {
  console.log(`nikkoe-backend listening on http://localhost:${port}`);
});
