from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from dystore.llm.types import ToolSchema
from dystore.sqlsandbox.executor import run_readonly_sql
from dystore.sqlsandbox.schema import describe_schema

ToolHandler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


@dataclass(slots=True)
class ChatTool:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: ToolHandler
    enabled: bool = True

    def schema(self) -> ToolSchema:
        return ToolSchema(name=self.name, description=self.description, parameters=self.parameters)


class ToolRegistry:
    def __init__(self, tools: list[ChatTool]) -> None:
        self._tools = {tool.name: tool for tool in tools}

    def schemas(self) -> list[ToolSchema]:
        return [tool.schema() for tool in self._tools.values() if tool.enabled]

    async def execute(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        tool = self._tools.get(name)
        if tool is None or not tool.enabled:
            return {"status": "error", "error": "unknown_tool", "tool": name}
        started = time.perf_counter()
        try:
            result = await tool.handler(arguments)
            return {"status": "ok", "tool": name, "latency_ms": int((time.perf_counter() - started) * 1000), "result": result}
        except Exception as exc:
            return {
                "status": "error",
                "tool": name,
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "error": f"{type(exc).__name__}: {exc}",
            }


async def _run_sql_tool(args: dict[str, Any]) -> dict[str, Any]:
    return await run_readonly_sql(str(args.get("sql") or ""), max_rows=int(args.get("max_rows") or 200))


async def _describe_schema_tool(args: dict[str, Any]) -> dict[str, Any]:
    return describe_schema(str(args.get("table_name") or args.get("table") or ""))


async def _render_table_tool(args: dict[str, Any]) -> dict[str, Any]:
    rows = list(args.get("rows") or [])
    columns = list(args.get("columns") or [])
    preview_limit = int(args.get("preview_limit") or 100)
    return {
        "kind": "table",
        "columns": columns,
        "rows": rows[:preview_limit],
        "capped": len(rows) > preview_limit,
        "source": args.get("source"),
    }


ALLOWED_CHART_KEYS = {"title", "tooltip", "legend", "xAxis", "yAxis", "series", "dataset", "grid"}


async def _render_chart_tool(args: dict[str, Any]) -> dict[str, Any]:
    option = dict(args.get("option") or {})
    invalid = sorted(set(option) - ALLOWED_CHART_KEYS)
    if invalid:
        return {"status": "error", "error": "unsupported_chart_keys", "keys": invalid}
    if _contains_script(option):
        return {"status": "error", "error": "script_not_allowed"}
    return {"kind": "chart", "option": option, "source": args.get("source")}


def default_registry() -> ToolRegistry:
    return ToolRegistry(
        [
            ChatTool(
                name="run_readonly_sql",
                description="Run a safe readonly SELECT against scraped merchant data.",
                parameters={
                    "type": "object",
                    "properties": {
                        "sql": {"type": "string"},
                        "max_rows": {"type": "integer", "minimum": 1, "maximum": 1000},
                    },
                    "required": ["sql"],
                },
                handler=_run_sql_tool,
            ),
            ChatTool(
                name="describe_schema",
                description="Describe allowed business-data table columns and usage hints.",
                parameters={
                    "type": "object",
                    "properties": {"table_name": {"type": "string"}},
                    "required": ["table_name"],
                },
                handler=_describe_schema_tool,
            ),
            ChatTool(
                name="render_table",
                description="Create a table render spec from columns and rows.",
                parameters={"type": "object", "properties": {"columns": {"type": "array"}, "rows": {"type": "array"}}},
                handler=_render_table_tool,
            ),
            ChatTool(
                name="render_chart",
                description="Create a validated ECharts render spec.",
                parameters={"type": "object", "properties": {"option": {"type": "object"}}},
                handler=_render_chart_tool,
            ),
        ]
    )


def _contains_script(value: Any) -> bool:
    if isinstance(value, str):
        lowered = value.lower()
        return "function" in lowered or "<script" in lowered or "javascript:" in lowered
    if isinstance(value, dict):
        return any(_contains_script(v) for v in value.values())
    if isinstance(value, list):
        return any(_contains_script(v) for v in value)
    return False
