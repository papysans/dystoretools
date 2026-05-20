import json

import pytest

from dystore.chat.agent import _build_context, _llm_visible_tool_result
from dystore.chat.service import add_message, create_conversation


def test_llm_visible_tool_result_strips_ui_rows() -> None:
    result = {
        "status": "ok",
        "tool": "run_readonly_sql",
        "result": {
            "llm_rows": [{"receiver_phone": "139****0001"}],
            "ui_rows": [{"receiver_phone": "13900000001"}],
            "columns": ["receiver_phone"],
        },
    }

    cleaned = _llm_visible_tool_result(result)

    assert cleaned["result"]["llm_rows"] == [{"receiver_phone": "139****0001"}]
    assert cleaned["result"]["ui_row_count"] == 1
    assert "ui_rows" not in cleaned["result"]
    assert "13900000001" not in repr(cleaned)
    assert "ui_rows" in result["result"]


@pytest.mark.asyncio
async def test_build_context_strips_persisted_ui_rows(session) -> None:
    conv = await create_conversation(session, title="ctx")
    await add_message(session, conversation_id=conv.id, role="user", content="查手机号")
    await add_message(
        session,
        conversation_id=conv.id,
        role="tool",
        kind="tool_result",
        content=json.dumps(
            {
                "result": {
                    "llm_rows": [{"receiver_phone": "139****0001"}],
                    "ui_rows": [{"receiver_phone": "13900000001"}],
                }
            },
            ensure_ascii=False,
        ),
        tool_name="run_readonly_sql",
        tool_call_id="call_1",
        tool_results_json={
            "result": {
                "llm_rows": [{"receiver_phone": "139****0001"}],
                "ui_rows": [{"receiver_phone": "13900000001"}],
            }
        },
    )

    context = await _build_context(session, conv.id)
    payload = "\n".join(message.content for message in context)

    assert "13900000001" not in payload
    assert "ui_rows" not in payload
    assert "139****0001" in payload
