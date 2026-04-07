import re

from app.dependencies import supabase

POSTGREST_PAGE = 1000
IN_CHUNK = 300


def dash_insensitive_pattern(query: str) -> str:
    """Regex that matches ``query`` with optional dashes between any characters."""
    stripped = query.replace("-", "")
    if not stripped:
        return ".*"
    chars = [re.escape(c) for c in stripped]
    return ".*" + "-?".join(chars) + ".*"


def batch_load(
    table: str, id_column: str, ids: list[int], select: str = "*", page_size: int = IN_CHUNK
) -> dict[int, dict]:
    if not ids:
        return {}
    result: dict[int, dict] = {}
    for i in range(0, len(ids), page_size):
        chunk = ids[i : i + page_size]
        resp = supabase.table(table).select(select).in_(id_column, chunk).execute()
        result.update({row[id_column]: row for row in (resp.data or [])})
    return result


def batch_in_load(table: str, select: str, column: str, ids: list, page_size: int = IN_CHUNK) -> list:
    """Like ``supabase.table(t).select(s).in_(col, ids).execute()`` but chunks
    the *ids* list so the URL never exceeds PostgREST limits."""
    if not ids:
        return []
    all_rows: list = []
    for i in range(0, len(ids), page_size):
        chunk = ids[i : i + page_size]
        resp = supabase.table(table).select(select).in_(column, chunk).execute()
        all_rows.extend(resp.data or [])
    return all_rows


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
