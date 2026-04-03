import type { DbClient } from "../../types/db.types.js";

export async function batchLoad<T>(
  db: DbClient,
  table: string,
  idColumn: string,
  ids: string[],
  select = "*",
): Promise<Map<string, T>> {
  if (ids.length === 0) return new Map();

  const { data, error } = await db
    .from(table)
    .select(select)
    .in(idColumn, ids);

  if (error) throw error;

  const result = new Map<string, T>();
  for (const row of data || []) {
    const key = (row as unknown as Record<string, unknown>)[idColumn] as string;
    result.set(key, row as unknown as T);
  }
  return result;
}
