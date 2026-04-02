import { Request, Response, NextFunction } from "express";
import { ZodError } from "zod";

export function errorHandler(err: unknown, _req: Request, res: Response, _next: NextFunction) {
  if (err instanceof ZodError) {
    res.status(400).json({
      error: "Validation failed",
      details: err.errors.map((e) => e.message),
    });
    return;
  }

  const message = err instanceof Error ? err.message : "Internal server error";
  console.error("[API Error]", err);
  res.status(500).json({ error: message });
}
