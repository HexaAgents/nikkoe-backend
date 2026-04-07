from app.dependencies import supabase

POSTGREST_PAGE = 1000


def batch_load(table: str, id_column: str, ids: list[int], select: str = "*") -> dict[int, dict]:
    if not ids:
        return {}
    response = supabase.table(table).select(select).in_(id_column, ids).execute()
    return {row[id_column]: row for row in (response.data or [])}


def paginated_fetch(query_builder, *, offset: int = 0, limit: int = 5000) -> tuple[list, int | None]:
    """Fetch up to *limit* rows from a PostgREST query, paging through the
    1 000-row ceiling automatically.  Returns ``(rows, total_count)``."""
    all_rows: list = []
    total: int | None = None
    remaining = limit

    while remaining > 0:
        page = min(remaining, POSTGREST_PAGE)
        resp = query_builder.range(offset, offset + page - 1).execute()
        batch = resp.data or []
        if total is None:
            total = resp.count
        all_rows.extend(batch)
        if len(batch) < page:
            break
        offset += page
        remaining -= page

    return all_rows, total or len(all_rows)
