from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger("eyex.tools.db")

_MAX_ROWS = 200
_MAX_CELL_LENGTH = 500


def _format_results(columns: list[str], rows: list[tuple[Any, ...]]) -> str:
    if not rows:
        return "(0 rows returned)"

    col_widths = [len(c) for c in columns]
    for row in rows[:5]:
        for i, val in enumerate(row):
            s = str(val) if val is not None else "NULL"
            if len(s) > _MAX_CELL_LENGTH:
                s = s[:_MAX_CELL_LENGTH] + "..."
            col_widths[i] = max(col_widths[i], min(len(s), 40))

    header = " | ".join(c.ljust(w) for c, w in zip(columns, col_widths))
    sep = "-+-".join("-" * w for w in col_widths)
    data_lines = []
    displayed = min(len(rows), _MAX_ROWS)
    for row in rows[:displayed]:
        cells = []
        for i, val in enumerate(row):
            s = str(val) if val is not None else "NULL"
            if len(s) > _MAX_CELL_LENGTH:
                s = s[:_MAX_CELL_LENGTH] + "..."
            cells.append(s.ljust(col_widths[i]))
        data_lines.append(" | ".join(cells))

    result = f"({displayed} row(s))\n\n{header}\n{sep}\n" + "\n".join(data_lines)
    if len(rows) > displayed:
        result += f"\n... and {len(rows) - displayed} more rows (truncated)"
    return result


@tool
async def db_query(sql: str, max_rows: int = 100) -> str:
    """Execute a SELECT SQL query against the database and return results as a formatted table."""
    from app.database import async_session_factory

    sql_upper = sql.strip().upper()
    if not sql_upper.startswith("SELECT") or "INTO" in sql_upper:
        return "Error: Only SELECT queries are allowed via db_query."

    limit = min(max_rows, _MAX_ROWS)

    try:
        async with async_session_factory() as session:
            from sqlalchemy import bindparam, text
            cleaned = sql.rstrip(";").rstrip()
            safe_sql = text(f"SELECT * FROM ({cleaned}) AS _q LIMIT :limit_val")
            safe_sql = safe_sql.bindparams(bindparam("limit_val", value=limit + 1))
            result = await session.execute(safe_sql)
            rows = result.fetchall()
            columns = list(result.keys())
            return _format_results(columns, rows)
    except Exception as exc:
        logger.error("DB query failed: %s | SQL: %.200s", exc, sql)
        return f"Error executing query: {exc}"


_ALLOWED_DML_TABLES = frozenset({
    "conversation_messages", "long_term_memory", "agent_memory_records",
})


@tool
async def db_execute(sql: str) -> str:
    """Execute an INSERT, UPDATE, or DELETE on allowed tables only (conversation_messages, long_term_memory, agent_memory_records). Returns number of affected rows."""
    from sqlalchemy import text

    from app.database import async_session_factory

    sql_upper = sql.strip().upper()
    if sql_upper.startswith("SELECT"):
        return "Error: Use db_query for SELECT statements"

    table_refs = {w.lower().rstrip("s") for w in sql.split() if w.isidentifier() and len(w) > 2}
    allowed_plural = {t for t in _ALLOWED_DML_TABLES}
    table_refs_singular = {t.rstrip("s") for t in table_refs}
    if not table_refs_singular.intersection({t.rstrip("s") for t in allowed_plural}):
        return "Error: Only allowed on memory tables: conversation_messages, long_term_memory, agent_memory_records"

    try:
        async with async_session_factory() as session:
            result = await session.execute(text(sql))
            await session.commit()
            rowcount = result.rowcount if result.rowcount != -1 else 0
            logger.info("DB execute affected %d rows on allowed tables", rowcount)
            return f"Success: {rowcount} row(s) affected"
    except Exception as exc:
        logger.error("DB execute failed: %s", exc)
        return f"Error executing statement: {exc}"


@tool
async def db_list_tables() -> str:
    """List all tables in the database with their schema information."""
    from sqlalchemy import text

    from app.config import get_settings
    from app.database import async_session_factory

    settings = get_settings()
    try:
        async with async_session_factory() as session:
            if "postgresql" in settings.database_url:
                result = await session.execute(
                    text("SELECT table_schema, table_name, pg_size_pretty(pg_total_relation_size(table_schema || '.' || table_name)) as size "
                         "FROM information_schema.tables "
                         "WHERE table_schema NOT IN ('pg_catalog', 'information_schema') "
                         "ORDER BY table_schema, table_name")
                )
            else:
                result = await session.execute(
                    text("SELECT table_name FROM information_schema.tables "
                         "WHERE table_schema NOT IN ('pg_catalog', 'information_schema') "
                         "ORDER BY table_name")
                )
            rows = result.fetchall()
            if not rows:
                return "No tables found in database"

            lines = [f"Tables ({len(rows)}):\n"]
            for row in rows:
                if len(row) >= 3:
                    lines.append(f"  {row[0]}.{row[1]}  ({row[2]})")
                else:
                    lines.append(f"  {row[0]}")
            return "\n".join(lines)
    except Exception as exc:
        logger.error("Failed to list tables: %s", exc)
        return f"Error listing tables: {exc}"


@tool
async def db_describe_table(table_name: str) -> str:
    """Describe the schema of a specific database table: columns, types, nullability, defaults."""
    from sqlalchemy import text

    from app.database import async_session_factory

    try:
        async with async_session_factory() as session:
            result = await session.execute(
                text("SELECT column_name, data_type, is_nullable, column_default, character_maximum_length "
                     "FROM information_schema.columns "
                     "WHERE table_name = :table_name "
                     "ORDER BY ordinal_position"),
                {"table_name": table_name},
            )
            rows = result.fetchall()
            if not rows:
                return f"Table '{table_name}' not found"

            lines = [f"Schema for '{table_name}':\n"]
            lines.append(f"  {'Column':30} {'Type':20} {'Nullable':10} {'Default':30}")
            lines.append(f"  {'-'*30} {'-'*20} {'-'*10} {'-'*30}")
            for row in rows:
                col, dtype, nullable, default, maxlen = row
                col_str = f"{col}"[:30]
                dtype_str = f"{dtype}"[:20]
                if maxlen:
                    dtype_str = f"{dtype}({maxlen})"[:20]
                null_str = "YES" if nullable == "YES" else "NO"
                default_str = str(default)[:30] if default else "None"
                lines.append(f"  {col_str:30} {dtype_str:20} {null_str:10} {default_str:30}")
            return "\n".join(lines)
    except Exception as exc:
        logger.error("Failed to describe table %s: %s", table_name, exc)
        return f"Error describing table: {exc}"
