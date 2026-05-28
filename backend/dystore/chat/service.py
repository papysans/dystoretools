from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from dystore.db.models import ChatConversation, ChatMessage


async def create_conversation(
    session: AsyncSession,
    *,
    title: str | None = None,
    provider_id: int | None = None,
    model_name: str | None = None,
) -> ChatConversation:
    row = ChatConversation(title=title or "新对话", provider_id=provider_id, model_name=model_name)
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def list_conversations(session: AsyncSession, *, limit: int = 100) -> list[ChatConversation]:
    rows = (
        await session.execute(
            select(ChatConversation)
            .where(ChatConversation.archived_at.is_(None))
            .order_by(desc(ChatConversation.updated_at))
            .limit(limit)
        )
    ).scalars().all()
    return list(rows)


async def list_messages(session: AsyncSession, conversation_id: int) -> list[ChatMessage]:
    rows = (
        await session.execute(
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.created_at, ChatMessage.id)
        )
    ).scalars().all()
    return list(rows)


async def add_message(
    session: AsyncSession,
    *,
    conversation_id: int,
    role: str,
    kind: str = "text",
    content: str | None = None,
    provider_id: int | None = None,
    model_name: str | None = None,
    ai_generation_id: int | None = None,
    tool_call_id: str | None = None,
    source_tool_call_id: str | None = None,
    tool_name: str | None = None,
    tool_calls_json=None,
    tool_results_json=None,
    render_spec_json=None,
    source_sql: str | None = None,
    status: str = "ok",
    error_msg: str | None = None,
    tokens_in: int = 0,
    tokens_out: int = 0,
    cost_cny: float = 0.0,
    latency_ms: int | None = None,
) -> ChatMessage:
    row = ChatMessage(
        conversation_id=conversation_id,
        role=role,
        kind=kind,
        content=content,
        provider_id=provider_id,
        model_name=model_name,
        ai_generation_id=ai_generation_id,
        tool_call_id=tool_call_id,
        source_tool_call_id=source_tool_call_id,
        tool_name=tool_name,
        tool_calls_json=tool_calls_json,
        tool_results_json=tool_results_json,
        render_spec_json=render_spec_json,
        source_sql=source_sql,
        status=status,
        error_msg=error_msg,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_cny=cost_cny,
        latency_ms=latency_ms,
    )
    session.add(row)
    await _touch_conversation(
        session,
        conversation_id,
        preview=content,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_cny=cost_cny,
    )
    await session.commit()
    await session.refresh(row)
    return row


async def _touch_conversation(
    session: AsyncSession,
    conversation_id: int,
    *,
    preview: str | None,
    tokens_in: int = 0,
    tokens_out: int = 0,
    cost_cny: float = 0.0,
) -> None:
    values = {
        "updated_at": datetime.utcnow(),
        "total_tokens_in": ChatConversation.total_tokens_in + tokens_in,
        "total_tokens_out": ChatConversation.total_tokens_out + tokens_out,
        "total_cost_cny": ChatConversation.total_cost_cny + cost_cny,
    }
    if preview:
        values["last_message_preview"] = preview[:255]
    await session.execute(update(ChatConversation).where(ChatConversation.id == conversation_id).values(**values))


def conversation_to_dict(row: ChatConversation) -> dict:
    return {
        "id": row.id,
        "title": row.title,
        "provider_id": row.provider_id,
        "model_name": row.model_name,
        "last_message_preview": row.last_message_preview,
        "total_tokens_in": row.total_tokens_in,
        "total_tokens_out": row.total_tokens_out,
        "total_cost_cny": row.total_cost_cny,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def message_to_dict(row: ChatMessage) -> dict:
    return {
        "id": row.id,
        "conversation_id": row.conversation_id,
        "role": row.role,
        "kind": row.kind,
        "content": row.content,
        "provider_id": row.provider_id,
        "model_name": row.model_name,
        "ai_generation_id": row.ai_generation_id,
        "tool_call_id": row.tool_call_id,
        "source_tool_call_id": row.source_tool_call_id,
        "tool_name": row.tool_name,
        "tool_calls": row.tool_calls_json,
        "tool_results": row.tool_results_json,
        "render_spec": row.render_spec_json,
        "source_sql": row.source_sql,
        "status": row.status,
        "error_msg": row.error_msg,
        "tokens_in": row.tokens_in,
        "tokens_out": row.tokens_out,
        "cost_cny": row.cost_cny,
        "latency_ms": row.latency_ms,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
