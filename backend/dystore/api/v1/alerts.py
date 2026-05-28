from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from dystore.db.models import Alert
from dystore.db.session import get_session
from dystore.ws.broker import publish

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


@router.get("")
async def list_alerts(
    kind: str | None = None,
    severity: str | None = None,
    acked: bool | None = None,
    limit: int = Query(100, le=500),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    filters = []
    if kind:
        filters.append(Alert.kind == kind)
    if severity:
        filters.append(Alert.severity == severity)
    if acked is True:
        filters.append(Alert.acked_at.is_not(None))
    elif acked is False:
        filters.append(Alert.acked_at.is_(None))
    q = select(Alert).where(and_(*filters)) if filters else select(Alert)
    rows = (await session.execute(q.order_by(desc(Alert.id)).limit(limit))).scalars().all()
    return [
        {
            "id": r.id,
            "kind": r.kind,
            "severity": r.severity,
            "payload": r.payload_json,
            "dispatched_at": r.dispatched_at.isoformat(),
            "acked_at": r.acked_at.isoformat() if r.acked_at else None,
        }
        for r in rows
    ]


@router.post("/{alert_id}/ack")
async def ack(alert_id: int, session: AsyncSession = Depends(get_session)) -> dict:
    row = (await session.execute(select(Alert).where(Alert.id == alert_id))).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, detail="alert not found")
    row.acked_at = datetime.utcnow()
    await session.commit()
    await publish("alerts", {"kind": "alert_acked", "id": alert_id, "acked_at": row.acked_at.isoformat()})
    return {"id": alert_id, "acked_at": row.acked_at.isoformat()}
