from __future__ import annotations

import asyncio
import time
from typing import Any

import sqlglot
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlglot import exp

from dystore.core.config import get_settings
from dystore.llm.pii_scrub import Scrubber
from dystore.sqlsandbox.policy import PII_COLUMNS, is_allowed_table

DEFAULT_MAX_ROWS = 1000
DEFAULT_TIMEOUT_SECONDS = 30


def validate_and_normalize_sql(sql: str, *, max_rows: int = DEFAULT_MAX_ROWS) -> tuple[str, list[str]]:
    try:
        expressions = sqlglot.parse(sql, read="mysql")
    except Exception as exc:
        raise ValueError(f"parse_error: {exc}") from exc
    if len(expressions) != 1:
        raise ValueError("multiple_statements_rejected")
    expression = expressions[0]
    if not isinstance(expression, exp.Select):
        raise ValueError("only_select_allowed")
    tables = sorted({table.name.lower() for table in expression.find_all(exp.Table)})
    if not tables:
        raise ValueError("from_required")
    for table in tables:
        if not is_allowed_table(table):
            raise ValueError(f"forbidden_table: {table}")
    capped = max(1, min(max_rows, DEFAULT_MAX_ROWS))
    limit = expression.args.get("limit")
    if limit is None:
        expression.set("limit", exp.Limit(expression=exp.Literal.number(capped)))
    else:
        current = _limit_value(limit)
        if current is None or current > capped:
            expression.set("limit", exp.Limit(expression=exp.Literal.number(capped)))
    return expression.sql(dialect="mysql"), tables


async def run_readonly_sql(sql: str, max_rows: int = 200, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        normalized_sql, tables = validate_and_normalize_sql(sql, max_rows=max_rows)
    except ValueError as exc:
        return _error("rejected", str(exc), started)
    try:
        rows, columns = await asyncio.wait_for(_execute(normalized_sql), timeout=timeout_seconds)
    except TimeoutError:
        return _error("timeout", "query_timeout", started, normalized_sql=normalized_sql)
    except Exception as exc:
        return _error("failed", f"{type(exc).__name__}: {exc}", started, normalized_sql=normalized_sql)
    row_dicts = [dict(zip(columns, row, strict=False)) for row in rows]
    max_out = max(1, min(max_rows, DEFAULT_MAX_ROWS))
    capped_rows = row_dicts[:max_out]
    return {
        "status": "ok",
        "normalized_sql": normalized_sql,
        "tables": tables,
        "columns": columns,
        "row_count": len(capped_rows),
        "capped": len(row_dicts) > len(capped_rows),
        "execution_ms": int((time.perf_counter() - started) * 1000),
        "llm_rows": mask_rows(capped_rows),
        "ui_rows": capped_rows,
    }


def mask_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scrubber = Scrubber()
    masked = []
    for row in rows:
        out = {}
        for key, value in row.items():
            if value is None:
                out[key] = value
            elif key.lower() in PII_COLUMNS:
                out[key] = scrubber.scrub(str(value))
            elif isinstance(value, str):
                out[key] = scrubber.scrub(value)
            else:
                out[key] = value
        masked.append(out)
    return masked


async def _execute(sql: str) -> tuple[list[tuple], list[str]]:
    settings = get_settings()
    engine = create_async_engine(settings.mysql_chat_readonly_dsn, future=True)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with maker() as session:
            result = await session.execute(text(f"/*+ MAX_EXECUTION_TIME({DEFAULT_TIMEOUT_SECONDS * 1000}) */ {sql}"))
            rows = result.fetchall()
            columns = list(result.keys())
            return [tuple(row) for row in rows], columns
    finally:
        await engine.dispose()


def _limit_value(limit: exp.Limit) -> int | None:
    expr = limit.args.get("expression")
    if isinstance(expr, exp.Literal) and expr.is_number:
        return int(expr.this)
    return None


def _error(status: str, error: str, started: float, *, normalized_sql: str | None = None) -> dict[str, Any]:
    return {
        "status": status,
        "normalized_sql": normalized_sql,
        "columns": [],
        "row_count": 0,
        "capped": False,
        "execution_ms": int((time.perf_counter() - started) * 1000),
        "llm_rows": [],
        "ui_rows": [],
        "error": error,
    }
