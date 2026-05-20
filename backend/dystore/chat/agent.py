from __future__ import annotations

import json
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from dystore.chat.service import add_message, list_messages, message_to_dict
from dystore.chat.tools import default_registry
from dystore.core.logging import get_logger
from dystore.llm.gateway import complete_messages
from dystore.llm.types import LLMMessage
from dystore.sqlsandbox.schema import schema_summary

MAX_AGENT_TURNS = 10
log = get_logger(__name__)
SYSTEM_PROMPT = """You are a merchant operations analyst for a local Douyin shop console.
Use tools to inspect scraped MySQL data. Never request or reveal raw PII. Prefer concise Chinese answers."""


async def run_agent_turn(
    session: AsyncSession,
    *,
    conversation_id: int,
    user_content: str,
    provider_id: int | None = None,
    model_name: str | None = None,
) -> AsyncIterator[dict]:
    log.info("chat.turn_start", conversation_id=conversation_id, provider_id=provider_id, model_name=model_name)
    user_msg = await add_message(session, conversation_id=conversation_id, role="user", content=user_content)
    yield {"event": "message", "data": message_to_dict(user_msg)}

    registry = default_registry()
    messages = await _build_context(session, conversation_id)
    for turn_index in range(MAX_AGENT_TURNS):
        result = await complete_messages(
            messages,
            kind="chat",
            provider_id=provider_id,
            model_name=model_name,
            tools=registry.schemas(),
            max_tokens=2048,
        )
        tool_calls = result.get("tool_calls") or []
        if not tool_calls:
            log.info(
                "chat.turn_done",
                conversation_id=conversation_id,
                tokens_in=result.get("tokens_in"),
                tokens_out=result.get("tokens_out"),
            )
            assistant = await add_message(
                session,
                conversation_id=conversation_id,
                role="assistant",
                content=result.get("text") or "",
                provider_id=result.get("provider_id"),
                model_name=result.get("model"),
                ai_generation_id=result.get("ai_generation_id"),
                tokens_in=int(result.get("tokens_in") or 0),
                tokens_out=int(result.get("tokens_out") or 0),
            )
            yield {"event": "delta", "data": {"content": assistant.content or ""}}
            yield {"event": "message", "data": message_to_dict(assistant)}
            yield {"event": "done", "data": {"message_id": assistant.id}}
            return

        assistant_call = await add_message(
            session,
            conversation_id=conversation_id,
            role="assistant",
            kind="tool_call",
            content=result.get("text") or "",
            provider_id=result.get("provider_id"),
            model_name=result.get("model"),
            ai_generation_id=result.get("ai_generation_id"),
            tool_calls_json=tool_calls,
            tokens_in=int(result.get("tokens_in") or 0),
            tokens_out=int(result.get("tokens_out") or 0),
        )
        yield {"event": "tool_call", "data": message_to_dict(assistant_call)}
        messages.append(
            LLMMessage(
                role="assistant",
                content=result.get("text") or "",
                tool_calls=tool_calls,
            )
        )
        for call in tool_calls:
            log.info("chat.tool_dispatch", conversation_id=conversation_id, tool=call.get("name"), turn_index=turn_index)
            tool_result = await registry.execute(call["name"], call.get("arguments") or {})
            tool_msg = await add_message(
                session,
                conversation_id=conversation_id,
                role="tool",
                kind=_tool_result_kind(tool_result),
                content=json.dumps(tool_result, ensure_ascii=False),
                tool_call_id=call.get("id"),
                source_tool_call_id=call.get("id"),
                tool_name=call.get("name"),
                tool_results_json=tool_result,
                render_spec_json=_tool_render_spec(tool_result),
                status=tool_result.get("status", "ok"),
                latency_ms=tool_result.get("latency_ms"),
            )
            yield {"event": "tool_result", "data": message_to_dict(tool_msg)}
            messages.append(
                LLMMessage(
                    role="tool",
                    content=json.dumps(tool_result, ensure_ascii=False),
                    tool_call_id=call.get("id"),
                    name=call.get("name"),
                )
            )

    log.warning("chat.agent_budget_exhausted", conversation_id=conversation_id, max_turns=MAX_AGENT_TURNS)
    failed = await add_message(
        session,
        conversation_id=conversation_id,
        role="assistant",
        kind="text",
        content="这次分析超过了工具调用上限，请缩小问题范围后重试。",
        status="failed",
        error_msg="agent_turn_budget_exhausted",
    )
    yield {"event": "error", "data": message_to_dict(failed)}


async def _build_context(session: AsyncSession, conversation_id: int) -> list[LLMMessage]:
    rows = await list_messages(session, conversation_id)
    first_user = next((row for row in rows if row.role == "user"), None)
    recent = rows[-20:]
    context = [
        LLMMessage(role="system", content=SYSTEM_PROMPT),
        LLMMessage(role="system", content=schema_summary()),
    ]
    if first_user is not None and first_user not in recent:
        context.append(LLMMessage(role="user", content=first_user.content or ""))
    for row in recent:
        if row.kind == "tool_call" and row.tool_calls_json:
            context.append(
                LLMMessage(
                    role="assistant",
                    content=row.content or "",
                    tool_calls=row.tool_calls_json if isinstance(row.tool_calls_json, list) else None,
                )
            )
            continue
        role = row.role if row.role in {"user", "assistant", "tool"} else "assistant"
        context.append(LLMMessage(role=role, content=row.content or "", tool_call_id=row.tool_call_id, name=row.tool_name))
    return context


def _tool_result_kind(tool_result: dict) -> str:
    result = tool_result.get("result") if isinstance(tool_result, dict) else None
    if isinstance(result, dict) and result.get("kind") in {"chart", "table"}:
        return str(result["kind"])
    return "tool_result"


def _tool_render_spec(tool_result: dict) -> dict | None:
    result = tool_result.get("result") if isinstance(tool_result, dict) else None
    if isinstance(result, dict) and result.get("kind") in {"chart", "table"}:
        return result
    return None
