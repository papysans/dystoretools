from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import desc, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from dystore.chat.service import add_message, list_messages, message_to_dict
from dystore.chat.tools import default_registry
from dystore.core.config import get_settings
from dystore.core.logging import get_logger
from dystore.db.models import (
    AftersaleCounts,
    Alert,
    CompassCoreData,
    CompassCoreTrend,
    ContentLive,
    DoudianAftersale,
    DoudianComment,
    DoudianGoods,
    DoudianOrder,
    DoudianStock,
    ExperienceScore,
    MemberDashboardDay,
    PeerGoods,
    ScrapeTaskRun,
    SessionEvent,
    ShopViolation,
)
from dystore.llm.gateway import complete_messages
from dystore.llm.types import LLMMessage
from dystore.sqlsandbox.schema import schema_summary

MAX_AGENT_TURNS = 10
log = get_logger(__name__)
SYSTEM_PROMPT = """You are a merchant operations analyst for a local Douyin shop console.
The authenticated user is the merchant operator and is authorized to inspect their own shop data, including order identifiers, buyer names, phone numbers, addresses, and other personal fields returned by approved tools.
Use tools to inspect scraped MySQL data. When the user asks for exact identifiers or contact fields, query and report the raw values returned by the tools.
Use the runtime_context system message to resolve relative dates, understand data freshness, and notice current scrape/auth state. If the requested period is newer than the latest available scraped data, say that clearly before analyzing.
When a table/chart artifact has already been rendered, do not repeat the same rows as a Markdown table in the final answer; provide only the concise conclusion or next-step analysis.
For doudian_order.status in chat analysis, use these labels unless the user provides a different mapping: 2=已付款, 4=已完成. Prefer concise Chinese answers and never invent data."""

_DATA_CONTEXT_TABLES = (
    ("doudian_order", DoudianOrder, {"pay_time": DoudianOrder.pay_time}),
    ("doudian_goods", DoudianGoods, {}),
    ("doudian_stock", DoudianStock, {}),
    ("doudian_comment", DoudianComment, {"created_at_src": DoudianComment.created_at_src}),
    (
        "doudian_aftersale",
        DoudianAftersale,
        {"created_at_src": DoudianAftersale.created_at_src, "deadline_at": DoudianAftersale.deadline_at},
    ),
    ("aftersale_counts", AftersaleCounts, {}),
    ("compass_core_data", CompassCoreData, {"begin_date": CompassCoreData.begin_date, "end_date": CompassCoreData.end_date}),
    ("compass_core_trend", CompassCoreTrend, {"date": CompassCoreTrend.date}),
    ("member_dashboard_day", MemberDashboardDay, {"date": MemberDashboardDay.date}),
    ("experience_score", ExperienceScore, {"date": ExperienceScore.date}),
    ("shop_violation", ShopViolation, {"created_at_src": ShopViolation.created_at_src}),
    ("peer_goods", PeerGoods, {}),
    ("content_live", ContentLive, {"start_at": ContentLive.start_at, "end_at": ContentLive.end_at}),
)


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
    messages = await _build_context(session, conversation_id, provider_id=provider_id, model_name=model_name)
    for turn_index in range(MAX_AGENT_TURNS):
        result = await complete_messages(
            messages,
            kind="chat",
            provider_id=provider_id,
            model_name=model_name,
            tools=registry.schemas(),
            max_tokens=2048,
            scrub_pii=False,
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


async def _build_context(
    session: AsyncSession,
    conversation_id: int,
    *,
    provider_id: int | None = None,
    model_name: str | None = None,
) -> list[LLMMessage]:
    rows = await list_messages(session, conversation_id)
    first_user = next((row for row in rows if row.role == "user"), None)
    recent = rows[-20:]
    context = [
        LLMMessage(role="system", content=SYSTEM_PROMPT),
        LLMMessage(
            role="system",
            content=await _build_runtime_context(session, conversation_id, provider_id=provider_id, model_name=model_name),
        ),
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
        if row.role == "tool" and row.tool_results_json:
            context.append(
                LLMMessage(
                    role="tool",
                    content=json.dumps(row.tool_results_json, ensure_ascii=False),
                    tool_call_id=row.tool_call_id,
                    name=row.tool_name,
                )
            )
            continue
        role = row.role if row.role in {"user", "assistant", "tool"} else "assistant"
        context.append(LLMMessage(role=role, content=row.content or "", tool_call_id=row.tool_call_id, name=row.tool_name))
    return context


async def _build_runtime_context(
    session: AsyncSession,
    conversation_id: int,
    *,
    provider_id: int | None,
    model_name: str | None,
) -> str:
    payload = await _runtime_context_payload(
        session,
        conversation_id,
        provider_id=provider_id,
        model_name=model_name,
    )
    return "runtime_context:\n" + json.dumps(payload, ensure_ascii=False, default=_json_default, separators=(",", ":"))


async def _runtime_context_payload(
    session: AsyncSession,
    conversation_id: int,
    *,
    provider_id: int | None,
    model_name: str | None,
) -> dict[str, Any]:
    settings = get_settings()
    now = _now_in_timezone(settings.tz)
    today = now.date()
    yesterday = today - timedelta(days=1)
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    return {
        "kind": "runtime_context",
        "current_time": {
            "timezone": settings.tz,
            "local_iso": now.isoformat(timespec="seconds"),
            "utc_iso": now.astimezone(timezone.utc).isoformat(timespec="seconds"),
            "unix_ms": int(now.timestamp() * 1000),
            "weekday": now.strftime("%A"),
        },
        "date_anchors": {
            "today": today.isoformat(),
            "yesterday": yesterday.isoformat(),
            "current_week_start_monday": week_start.isoformat(),
            "current_month_start": month_start.isoformat(),
        },
        "conversation": {
            "conversation_id": conversation_id,
            "requested_provider_id": provider_id,
            "requested_model_name": model_name,
        },
        "business_semantics": {
            "locale": "zh-CN",
            "currency": "CNY",
            "platform": "抖店 / Douyin merchant console",
            "relative_date_policy": "Interpret relative dates such as 今天/昨天/最近7天 using current_time.timezone.",
            "order_status_labels": {"2": "已付款", "4": "已完成"},
        },
        "data_snapshot": {
            "note": "row_count is local MySQL rows. scraped_at is ingestion time. source_ranges are source/business timestamps.",
            "tables": await _data_snapshot(session),
        },
        "ops_snapshot": await _ops_snapshot(session),
    }


def _now_in_timezone(tz_name: str) -> datetime:
    try:
        tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        tz = ZoneInfo("Asia/Shanghai")
    return datetime.now(tz)


async def _data_snapshot(session: AsyncSession) -> dict[str, Any]:
    snapshot: dict[str, Any] = {}
    for table_name, model, source_columns in _DATA_CONTEXT_TABLES:
        snapshot[table_name] = await _table_snapshot(session, model, source_columns)
    return snapshot


async def _table_snapshot(session: AsyncSession, model: Any, source_columns: dict[str, Any]) -> dict[str, Any]:
    columns = [func.count().label("row_count")]
    has_scraped_at = hasattr(model, "scraped_at")
    if has_scraped_at:
        columns.extend([func.min(model.scraped_at).label("scraped_at_min"), func.max(model.scraped_at).label("scraped_at_max")])
    for name, column in source_columns.items():
        columns.extend([func.min(column).label(f"{name}_min"), func.max(column).label(f"{name}_max")])

    try:
        row = (await session.execute(select(*columns).select_from(model))).one()
    except SQLAlchemyError as exc:
        return {"error": f"{type(exc).__name__}: {exc}"[:300]}

    index = 0
    payload: dict[str, Any] = {"row_count": int(row[index] or 0)}
    index += 1
    if has_scraped_at:
        payload["scraped_at_min"] = row[index]
        payload["scraped_at_max"] = row[index + 1]
        index += 2
    source_ranges: dict[str, dict[str, Any]] = {}
    for name in source_columns:
        source_ranges[name] = {"min": row[index], "max": row[index + 1]}
        index += 2
    if source_ranges:
        payload["source_ranges"] = source_ranges
    return payload


async def _ops_snapshot(session: AsyncSession) -> dict[str, Any]:
    latest_session_event = (
        await session.execute(select(SessionEvent).order_by(desc(SessionEvent.occurred_at), desc(SessionEvent.id)).limit(1))
    ).scalar_one_or_none()
    recent_runs = (
        await session.execute(select(ScrapeTaskRun).order_by(desc(ScrapeTaskRun.id)).limit(5))
    ).scalars().all()
    open_alert_count = (
        await session.execute(select(func.count()).select_from(Alert).where(Alert.acked_at.is_(None)))
    ).scalar_one()

    return {
        "latest_session_event": None
        if latest_session_event is None
        else {
            "kind": latest_session_event.kind,
            "occurred_at": latest_session_event.occurred_at,
            "payload": latest_session_event.payload_json,
        },
        "recent_scrape_runs": [
            {
                "target": row.target,
                "subsystem": row.subsystem,
                "status": row.status,
                "items_count": row.items_count,
                "started_at": row.started_at,
                "finished_at": row.finished_at,
                "error_msg": row.error_msg,
            }
            for row in recent_runs
        ],
        "open_alert_count": int(open_alert_count or 0),
    }


def _json_default(value: Any) -> str:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


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
