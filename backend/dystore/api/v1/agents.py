from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from dystore.chat import custom_agents as service
from dystore.db.session import get_session

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=512)
    system_prompt: str | None = None
    provider_id: int | None = None
    model_name: str | None = Field(default=None, max_length=128)
    tools: list[str] | None = None
    enabled: bool = True


class AgentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=512)
    system_prompt: str | None = None
    provider_id: int | None = None
    model_name: str | None = Field(default=None, max_length=128)
    tools: list[str] | None = None
    enabled: bool | None = None


class AgentRunRequest(BaseModel):
    prompt: str = Field(min_length=1)


class ScheduleCreate(BaseModel):
    agent_id: int
    name: str = Field(min_length=1, max_length=128)
    prompt: str = Field(min_length=1)
    cron: str = Field(min_length=1, max_length=64)
    timezone: str = Field(default="Asia/Shanghai", max_length=64)
    enabled: bool = True


class ScheduleUpdate(BaseModel):
    agent_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=128)
    prompt: str | None = Field(default=None, min_length=1)
    cron: str | None = Field(default=None, min_length=1, max_length=64)
    timezone: str | None = Field(default=None, max_length=64)
    enabled: bool | None = None


@router.get("")
async def list_agents(session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    rows = await service.list_agents(session)
    return {"items": [service.agent_to_dict(row) for row in rows]}


@router.post("")
async def create_agent(req: AgentCreate, session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    row = await service.create_agent(
        session,
        name=req.name,
        description=req.description,
        system_prompt=req.system_prompt,
        provider_id=req.provider_id,
        model_name=req.model_name,
        tools=req.tools,
        enabled=req.enabled,
    )
    return service.agent_to_dict(row)


@router.get("/{agent_id}")
async def get_agent(agent_id: int, session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    row = await service.get_agent(session, agent_id)
    if row is None:
        raise HTTPException(404, detail="agent not found")
    return service.agent_to_dict(row)


@router.patch("/{agent_id}")
async def update_agent(agent_id: int, req: AgentUpdate, session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    row = await service.update_agent(session, agent_id, req.model_dump(exclude_unset=True))
    if row is None:
        raise HTTPException(404, detail="agent not found")
    return service.agent_to_dict(row)


@router.delete("/{agent_id}")
async def delete_agent(agent_id: int, session: AsyncSession = Depends(get_session)) -> dict[str, int]:
    ok = await service.delete_agent(session, agent_id)
    if not ok:
        raise HTTPException(404, detail="agent not found")
    return {"deleted": agent_id}


@router.post("/{agent_id}/runs")
async def run_agent(agent_id: int, req: AgentRunRequest) -> dict[str, Any]:
    try:
        row = await service.dispatch_agent_run(agent_id, prompt=req.prompt)
    except ValueError as exc:
        raise HTTPException(404, detail=str(exc))
    return service.run_to_dict(row)


@router.get("/runs/recent")
async def list_runs(
    agent_id: int | None = None,
    limit: int = 100,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    rows = await service.list_runs(session, agent_id=agent_id, limit=min(max(limit, 1), 200))
    return {"items": [service.run_to_dict(row) for row in rows]}


@router.get("/schedules/all")
async def list_schedules(agent_id: int | None = None, session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    rows = await service.list_schedules(session, agent_id=agent_id)
    return {"items": [service.schedule_to_dict(row) for row in rows]}


@router.post("/schedules")
async def create_schedule(req: ScheduleCreate, session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    agent = await service.get_agent(session, req.agent_id)
    if agent is None:
        raise HTTPException(404, detail="agent not found")
    try:
        row = await service.create_schedule(
            session,
            agent_id=req.agent_id,
            name=req.name,
            prompt=req.prompt,
            cron=req.cron,
            timezone=req.timezone,
            enabled=req.enabled,
        )
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc))
    return service.schedule_to_dict(row)


@router.patch("/schedules/{schedule_id}")
async def update_schedule(schedule_id: int, req: ScheduleUpdate, session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    values = req.model_dump(exclude_unset=True)
    if "agent_id" in values and values["agent_id"] is not None:
        agent = await service.get_agent(session, values["agent_id"])
        if agent is None:
            raise HTTPException(404, detail="agent not found")
    try:
        row = await service.update_schedule(session, schedule_id, values)
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc))
    if row is None:
        raise HTTPException(404, detail="schedule not found")
    return service.schedule_to_dict(row)


@router.delete("/schedules/{schedule_id}")
async def delete_schedule(schedule_id: int, session: AsyncSession = Depends(get_session)) -> dict[str, int]:
    ok = await service.delete_schedule(session, schedule_id)
    if not ok:
        raise HTTPException(404, detail="schedule not found")
    return {"deleted": schedule_id}
