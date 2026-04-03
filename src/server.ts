import "dotenv/config";
import express from "express";
import cors from "cors";
import { errorHandler } from "./middleware/errorHandler.js";
import {
  requireAuth,
  receiptRouter,
  saleRouter,
  itemRouter,
  supplierRouter,
  locationRouter,
  categoryRouter,
  channelRouter,
  customerRouter,
  inventoryRouter,
  userRouter,
  supplierQuoteRouter,
} from "./container.js";

const app = express();
const port = parseInt(process.env.PORT || "3000", 10);

app.use(cors({ origin: process.env.CORS_ORIGIN || true, credentials: true }));
app.use(express.json());

app.get("/api/health", (_req, res) => {
  res.json({ status: "ok", timestamp: new Date().toISOString() });
});

app.use("/api/receipts", requireAuth, receiptRouter);
app.use("/api/sales", requireAuth, saleRouter);
app.use("/api/items", requireAuth, itemRouter);
app.use("/api/suppliers", requireAuth, supplierRouter);
app.use("/api/locations", requireAuth, locationRouter);
app.use("/api/categories", requireAuth, categoryRouter);
app.use("/api/channels", requireAuth, channelRouter);
app.use("/api/customers", requireAuth, customerRouter);
app.use("/api/inventory", requireAuth, inventoryRouter);
app.use("/api/users", requireAuth, userRouter);
app.use("/api/supplier-quotes", requireAuth, supplierQuoteRouter);

app.use(errorHandler);

app.listen(port, () => {
  console.log(`nikkoe-backend listening on http://localhost:${port}`);
});
