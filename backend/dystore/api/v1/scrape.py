import asyncio
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from dystore.core.logging import get_logger
from dystore.db.models import ScrapeTaskRun
from dystore.db.session import SessionLocal, get_session
from dystore.scheduler.scheduler import run_target_by_name
from dystore.scraper.antidetect import QuietHoursViolation
from dystore.scraper.spec_loader import load_all
from dystore.ws.broker import publish

log = get_logger(__name__)
router = APIRouter(prefix="/api/v1/scrape", tags=["scrape"])


async def _record_manual_failure(target: str, subsystem: str, kind: str, msg: str) -> None:
    """Persist a scrape_task_run row for failures that occur before the engine runs."""
    now = datetime.utcnow()
    async with SessionLocal() as s:
        row = ScrapeTaskRun(
            target=target,
            subsystem=subsystem,
            started_at=now,
            finished_at=now,
            status=kind,
            items_count=0,
            error_msg=msg[:2000],
        )
        s.add(row)
        await s.commit()
        await s.refresh(row)
    await publish("tasks", {"kind": "task_failed", "run_id": row.id, "target": target, "error": msg[:200]})


@router.post("/run")
async def run_now(target: str) -> dict:
    specs = load_all()
    if target not in specs:
        raise HTTPException(status_code=404, detail=f"unknown target: {target}")
    subsystem = specs[target].subsystem

    async def _run() -> None:
        try:
            await run_target_by_name(target)
        except QuietHoursViolation as e:
            await _record_manual_failure(target, subsystem, "skipped_quiet_hours", str(e))
        except Exception as e:
            log.exception("scrape.manual_run_failed", target=target)
            await _record_manual_failure(target, subsystem, "failed", f"{type(e).__name__}: {e}")

    asyncio.create_task(_run())
    return {"status": "dispatched", "target": target}


@router.get("/runs")
async def list_runs(
    target: str | None = None,
    limit: int = Query(50, le=500),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    q = select(ScrapeTaskRun).order_by(desc(ScrapeTaskRun.id)).limit(limit)
    if target:
        q = q.where(ScrapeTaskRun.target == target)
    rows = (await session.execute(q)).scalars().all()
    return [
        {
            "id": r.id,
            "target": r.target,
            "subsystem": r.subsystem,
            "status": r.status,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "items_count": r.items_count,
            "error_msg": r.error_msg,
        }
        for r in rows
    ]


@router.get("/targets")
async def list_targets() -> list[dict]:
    specs = load_all()
    return [
        {
            "target": s.target,
            "subsystem": s.subsystem,
            "nav_url": s.nav.url,
            "cron": s.schedule.cron,
            "sink_table": s.sink.table,
        }
        for s in specs.values()
    ]
