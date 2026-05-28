from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dystore.api.v1._enums import AFTERSALE_CANONICAL_DIMS, AFTERSALE_STATUS, AFTERSALE_TYPE
from dystore.db.models import AftersaleCounts, DoudianAftersale
from dystore.db.session import get_session

router = APIRouter(prefix="/api/v1/aftersale", tags=["aftersale"])


def _coerce_type(raw: str | None) -> int | None:
    """`DoudianAftersale.type` is String(32) holding numeric strings like '0','1','3'."""
    if raw and raw.isdigit():
        return int(raw)
    return None


@router.get("")
async def list_aftersale(
    type: str | None = None,
    status: int | None = None,
    page: int = 0,
    page_size: int = Query(20, le=200),
    session: AsyncSession = Depends(get_session),
) -> dict:
    filters = []
    if type is not None:
        filters.append(DoudianAftersale.type == type)
    if status is not None:
        filters.append(DoudianAftersale.status == status)

    total_q = select(func.count(DoudianAftersale.id))
    q = (
        select(DoudianAftersale)
        .order_by(desc(DoudianAftersale.scraped_at), desc(DoudianAftersale.id))
        .offset(page * page_size)
        .limit(page_size)
    )
    if filters:
        total_q = total_q.where(*filters)
        q = q.where(*filters)

    total = (await session.execute(total_q)).scalar_one()
    rows = (await session.execute(q)).scalars().all()

    items = []
    for r in rows:
        type_int = _coerce_type(r.type)
        status_int = r.status
        items.append(
            {
                "aftersale_id": r.aftersale_id,
                "order_sn": r.order_sn,
                "type": type_int,
                "type_label": AFTERSALE_TYPE.get(type_int) if type_int is not None else None,
                "status": status_int,
                "status_label": AFTERSALE_STATUS.get(status_int) if status_int is not None else None,
                "refund_amount": float(r.refund_amount) if r.refund_amount is not None else 0.0,
                "deadline_at": r.deadline_at.isoformat() if r.deadline_at else None,
                "scraped_at": r.scraped_at.isoformat() if r.scraped_at else None,
            }
        )

    return {"total": int(total), "items": items}


@router.get("/counts")
async def aftersale_counts(session: AsyncSession = Depends(get_session)) -> dict:
    ts = (await session.execute(select(func.max(AftersaleCounts.scraped_at)))).scalar_one_or_none()
    dims: dict[str, int] = {k: 0 for k in AFTERSALE_CANONICAL_DIMS}
    if ts is None:
        return {"scraped_at": None, "dims": dims}

    rows = (
        await session.execute(
            select(AftersaleCounts.dim, AftersaleCounts.count).where(
                AftersaleCounts.scraped_at == ts,
                AftersaleCounts.dim.in_(AFTERSALE_CANONICAL_DIMS),
            )
        )
    ).all()
    for dim, count in rows:
        dims[dim] = int(count)

    return {"scraped_at": ts.isoformat(), "dims": dims}
