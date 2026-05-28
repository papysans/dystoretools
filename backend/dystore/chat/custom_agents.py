from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from dystore.chat.agent import run_agent_turn
from dystore.chat.service import create_conversation
from dystore.db.models import AgentRun, AgentSchedule, UserAgent
from dystore.db.session import SessionLocal
from dystore.scheduler.scheduler import get_scheduler
from dystore.ws.broker import publish

AGENT_SCHEDULE_JOB_PREFIX = "agent-schedule-"
DEFAULT_AGENT_PROMPT = "你是一个用户自定义的抖店运营智能体。请按用户给定目标执行分析，必要时使用可用工具读取本地数据，输出简洁、可执行的中文结论。"


def schedule_to_dict(row: AgentSchedule) -> dict[str, Any]:
    return {
        "id": row.id,
        "agent_id": row.agent_id,
        "name": row.name,
        "prompt": row.prompt,
        "cron": row.cron,
        "timezone": row.timezone,
        "enabled": row.enabled,
        "last_run_at": row.last_run_at.isoformat() if row.last_run_at else None,
        "next_run_at": row.next_run_at.isoformat() if row.next_run_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def agent_to_dict(row: UserAgent) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.name,
        "description": row.description,
        "system_prompt": row.system_prompt,
        "provider_id": row.provider_id,
        "model_name": row.model_name,
        "tools": row.tools_json or [],
        "enabled": row.enabled,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def run_to_dict(row: AgentRun) -> dict[str, Any]:
    return {
        "id": row.id,
        "agent_id": row.agent_id,
        "schedule_id": row.schedule_id,
        "conversation_id": row.conversation_id,
        "trigger_kind": row.trigger_kind,
        "prompt": row.prompt,
        "status": row.status,
        "result_text": row.result_text,
        "error_msg": row.error_msg,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "finished_at": row.finished_at.isoformat() if row.finished_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


async def list_agents(session: AsyncSession) -> list[UserAgent]:
    rows = (await session.execute(select(UserAgent).order_by(desc(UserAgent.updated_at)))).scalars().all()
    return list(rows)


async def create_agent(
    session: AsyncSession,
    *,
    name: str,
    description: str | None,
    system_prompt: str | None,
    provider_id: int | None,
    model_name: str | None,
    tools: list[str] | None,
    enabled: bool,
) -> UserAgent:
    row = UserAgent(
        name=name,
        description=description,
        system_prompt=system_prompt or DEFAULT_AGENT_PROMPT,
        provider_id=provider_id,
        model_name=model_name,
        tools_json=tools or [],
        enabled=enabled,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def get_agent(session: AsyncSession, agent_id: int) -> UserAgent | None:
    return await session.get(UserAgent, agent_id)


async def update_agent(session: AsyncSession, agent_id: int, values: dict[str, Any]) -> UserAgent | None:
    row = await get_agent(session, agent_id)
    if row is None:
        return None
    for key, value in values.items():
        if key == "tools":
            row.tools_json = value or []
        elif hasattr(row, key):
            setattr(row, key, value)
    await session.commit()
    await session.refresh(row)
    return row


async def delete_agent(session: AsyncSession, agent_id: int) -> bool:
    row = await get_agent(session, agent_id)
    if row is None:
        return False
    schedules = (await session.execute(select(AgentSchedule).where(AgentSchedule.agent_id == agent_id))).scalars().all()
    for schedule in schedules:
        remove_agent_schedule_job(schedule.id)
        await session.delete(schedule)
    await session.delete(row)
    await session.commit()
    return True


async def create_schedule(
    session: AsyncSession,
    *,
    agent_id: int,
    name: str,
    prompt: str,
    cron: str,
    timezone: str,
    enabled: bool,
) -> AgentSchedule:
    validate_cron(cron, timezone)
    row = AgentSchedule(
        agent_id=agent_id,
        name=name,
        prompt=prompt,
        cron=cron,
        timezone=timezone,
        enabled=enabled,
    )
    row.next_run_at = next_run_at(cron, timezone)
    session.add(row)
    await session.commit()
    await session.refresh(row)
    register_agent_schedule_job(row)
    return row


async def list_schedules(session: AsyncSession, *, agent_id: int | None = None) -> list[AgentSchedule]:
    q = select(AgentSchedule).order_by(desc(AgentSchedule.updated_at))
    if agent_id is not None:
        q = q.where(AgentSchedule.agent_id == agent_id)
    return list((await session.execute(q)).scalars().all())


async def update_schedule(session: AsyncSession, schedule_id: int, values: dict[str, Any]) -> AgentSchedule | None:
    row = await session.get(AgentSchedule, schedule_id)
    if row is None:
        return None
    cron = values.get("cron", row.cron)
    timezone = values.get("timezone", row.timezone)
    validate_cron(cron, timezone)
    for key, value in values.items():
        if hasattr(row, key):
            setattr(row, key, value)
    row.next_run_at = next_run_at(row.cron, row.timezone) if row.enabled else None
    await session.commit()
    await session.refresh(row)
    register_agent_schedule_job(row)
    return row


async def delete_schedule(session: AsyncSession, schedule_id: int) -> bool:
    row = await session.get(AgentSchedule, schedule_id)
    if row is None:
        return False
    remove_agent_schedule_job(schedule_id)
    await session.delete(row)
    await session.commit()
    return True


async def list_runs(session: AsyncSession, *, agent_id: int | None = None, limit: int = 100) -> list[AgentRun]:
    q = select(AgentRun).order_by(desc(AgentRun.id)).limit(limit)
    if agent_id is not None:
        q = q.where(AgentRun.agent_id == agent_id)
    return list((await session.execute(q)).scalars().all())


async def dispatch_agent_run(agent_id: int, *, prompt: str, trigger_kind: str = "manual", schedule_id: int | None = None) -> AgentRun:
    async with SessionLocal() as session:
        agent = await session.get(UserAgent, agent_id)
        if agent is None or not agent.enabled:
            raise ValueError("agent not found or disabled")
        row = AgentRun(agent_id=agent_id, schedule_id=schedule_id, trigger_kind=trigger_kind, prompt=prompt, status="queued")
        session.add(row)
        await session.commit()
        await session.refresh(row)
        run_id = row.id
    asyncio.create_task(execute_agent_run(run_id))
    return row


async def execute_agent_run(run_id: int) -> None:
    async with SessionLocal() as session:
        run = await session.get(AgentRun, run_id)
        if run is None:
            return
        agent = await session.get(UserAgent, run.agent_id)
        if agent is None:
            run.status = "failed"
            run.error_msg = "agent not found"
            run.finished_at = datetime.utcnow()
            await session.commit()
            return
        run.status = "running"
        run.started_at = datetime.utcnow()
        await session.commit()
        await session.refresh(run)
        try:
            conversation = await create_conversation(
                session,
                title=f"{agent.name} · {run.trigger_kind}",
                provider_id=agent.provider_id,
                model_name=agent.model_name,
            )
            run.conversation_id = conversation.id
            await session.commit()
            prompt = f"{agent.system_prompt}\n\n用户任务：{run.prompt}"
            final_text = ""
            async for item in run_agent_turn(
                session,
                conversation_id=conversation.id,
                user_content=prompt,
                provider_id=agent.provider_id,
                model_name=agent.model_name,
            ):
                if item["event"] == "delta":
                    final_text += item["data"].get("content", "")
            run.status = "done"
            run.result_text = final_text[:65535]
            run.finished_at = datetime.utcnow()
            await session.commit()
            await publish("tasks", {"kind": "agent_run_done", "target": f"agent:{agent.name}", "run_id": run.id})
        except Exception as exc:
            run.status = "failed"
            run.error_msg = f"{type(exc).__name__}: {exc}"[:2048]
            run.finished_at = datetime.utcnow()
            await session.commit()
            await publish("tasks", {"kind": "agent_run_failed", "target": f"agent:{agent.name}", "run_id": run.id, "error": run.error_msg})


async def execute_schedule(schedule_id: int) -> None:
    async with SessionLocal() as session:
        schedule = await session.get(AgentSchedule, schedule_id)
        if schedule is None or not schedule.enabled:
            return
        schedule.last_run_at = datetime.utcnow()
        schedule.next_run_at = next_run_at(schedule.cron, schedule.timezone)
        await session.commit()
        agent_id = schedule.agent_id
        prompt = schedule.prompt
    await dispatch_agent_run(agent_id, prompt=prompt, trigger_kind="schedule", schedule_id=schedule_id)


def validate_cron(cron: str, timezone: str) -> None:
    parts = cron.split()
    if len(parts) != 5:
        raise ValueError("cron must have 5 fields: minute hour day month weekday")
    CronTrigger.from_crontab(cron, timezone=timezone)


def next_run_at(cron: str, timezone: str) -> datetime | None:
    trigger = CronTrigger.from_crontab(cron, timezone=timezone)
    value = trigger.get_next_fire_time(None, datetime.now(trigger.timezone))
    if value is None:
        return None
    return value.replace(tzinfo=None)


def schedule_job_id(schedule_id: int) -> str:
    return f"{AGENT_SCHEDULE_JOB_PREFIX}{schedule_id}"


def register_agent_schedule_job(schedule: AgentSchedule) -> None:
    scheduler = get_scheduler()
    job_id = schedule_job_id(schedule.id)
    scheduler.remove_job(job_id) if scheduler.get_job(job_id) else None
    if not schedule.enabled:
        return
    trigger = CronTrigger.from_crontab(schedule.cron, timezone=schedule.timezone)
    scheduler.add_job(execute_schedule, trigger, args=[schedule.id], id=job_id, replace_existing=True)


def remove_agent_schedule_job(schedule_id: int) -> None:
    scheduler = get_scheduler()
    job_id = schedule_job_id(schedule_id)
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)


async def register_all_agent_schedule_jobs() -> None:
    async with SessionLocal() as session:
        rows = (await session.execute(select(AgentSchedule).where(AgentSchedule.enabled.is_(True)))).scalars().all()
    for row in rows:
        register_agent_schedule_job(row)
