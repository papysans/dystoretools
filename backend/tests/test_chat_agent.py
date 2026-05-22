import json

import pytest

from dystore.chat.agent import _build_context
from dystore.chat.service import add_message, create_conversation


@pytest.mark.asyncio
async def test_build_context_keeps_ui_rows_for_chat_analysis(session) -> None:
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

    assert "ui_rows" in payload
    assert "13900000001" in payload


@pytest.mark.asyncio
async def test_build_context_includes_runtime_context(session) -> None:
    conv = await create_conversation(session, title="runtime")
    await add_message(session, conversation_id=conv.id, role="user", content="今天订单怎么样？")

    context = await _build_context(session, conv.id, provider_id=1, model_name="deepseek-chat")
    runtime = next(message.content for message in context if message.content.startswith("runtime_context:"))

    assert '"current_time"' in runtime
    assert '"today"' in runtime
    assert '"requested_provider_id":1' in runtime
    assert '"requested_model_name":"deepseek-chat"' in runtime
    assert '"data_snapshot"' in runtime
    assert '"doudian_order"' in runtime
    assert '"ops_snapshot"' in runtime
