from app.dependencies import supabase


def batch_load(
    table: str, id_column: str, ids: list[int], select: str = "*"
) -> dict[int, dict]:
    if not ids:
        return {}
    response = supabase.table(table).select(select).in_(id_column, ids).execute()
    return {row[id_column]: row for row in (response.data or [])}
