import pytest

from dystore.chat import tools
from dystore.chat.tools import default_registry


@pytest.mark.asyncio
async def test_tool_schemas_export() -> None:
    schemas = default_registry().schemas()
    names = {schema.name for schema in schemas}
    assert {"run_readonly_sql", "describe_schema", "render_table", "render_chart"} <= names


@pytest.mark.asyncio
async def test_unknown_tool_returns_error() -> None:
    result = await default_registry().execute("missing", {})
    assert result["status"] == "error"


@pytest.mark.asyncio
async def test_render_chart_rejects_script() -> None:
    result = await default_registry().execute("render_chart", {"option": {"series": ["function(){alert(1)}"]}})
    assert result["result"]["status"] == "error"


@pytest.mark.asyncio
async def test_render_table_caps_rows() -> None:
    result = await default_registry().execute(
        "render_table",
        {"columns": ["a"], "rows": [{"a": i} for i in range(5)], "preview_limit": 2},
    )
    assert result["result"]["capped"] is True
    assert len(result["result"]["rows"]) == 2


@pytest.mark.asyncio
async def test_sql_tool_keeps_ui_rows_for_frontend(monkeypatch) -> None:
    async def fake_run_readonly_sql(sql: str, max_rows: int) -> dict:
        return {
            "status": "ok",
            "normalized_sql": sql,
            "columns": [{"name": "receiver_phone"}],
            "llm_rows": [{"receiver_phone": "139****0001"}],
            "ui_rows": [{"receiver_phone": "13900000001"}],
            "row_count": 1,
        }

    monkeypatch.setattr(tools, "run_readonly_sql", fake_run_readonly_sql)

    result = await default_registry().execute(
        "run_readonly_sql",
        {"sql": "SELECT receiver_phone FROM doudian_order", "max_rows": 10},
    )

    payload = result["result"]
    assert payload["ui_rows"] == [{"receiver_phone": "13900000001"}]
    assert payload["llm_rows"] == [{"receiver_phone": "139****0001"}]
