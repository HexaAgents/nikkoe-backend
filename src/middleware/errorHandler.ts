import { Request, Response, NextFunction } from "express";
import { ZodError } from "zod";
import { AppError } from "../errors/index.js";

interface PostgrestError {
  code: string;
  message: string;
  details: string;
}

function isPostgrestError(err: unknown): err is PostgrestError {
  return (
    typeof err === "object" &&
    err !== null &&
    "code" in err &&
    "message" in err &&
    "details" in err
  );
}

const PG_ERROR_MAP: Record<string, { status: number; message: string }> = {
  "23505": { status: 409, message: "Duplicate record" },
  "23503": { status: 409, message: "Referenced record does not exist" },
  "23502": { status: 400, message: "Missing required field" },
};

export function errorHandler(err: unknown, _req: Request, res: Response, _next: NextFunction) {
  if (err instanceof ZodError) {
    res.status(400).json({
      error: "Validation failed",
      details: err.errors.map((e) => e.message),
    });
    return;
  }

  if (err instanceof AppError) {
    res.status(err.statusCode).json({ error: err.message });
    return;
  }

  if (isPostgrestError(err)) {
    const mapped = PG_ERROR_MAP[err.code];
    if (mapped) {
      res.status(mapped.status).json({ error: mapped.message });
      return;
    }
  }

  const message = err instanceof Error ? err.message : "Internal server error";
  console.error("[API Error]", err);
  res.status(500).json({ error: message });
}
