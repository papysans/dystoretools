from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from dystore.db.models import DoudianOrder
from dystore.db.session import get_session

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


@router.get("")
async def list_orders(
    status: int | None = None,
    page: int = 0,
    page_size: int = Query(20, le=200),
    session: AsyncSession = Depends(get_session),
) -> dict:
    q = select(DoudianOrder).order_by(desc(DoudianOrder.pay_time)).offset(page * page_size).limit(page_size)
    if status is not None:
        q = q.where(DoudianOrder.status == status)
    rows = (await session.execute(q)).scalars().all()
    return {
        "items": [
            {
                "id": r.id,
                "order_sn": r.order_sn,
                "goods_name": r.goods_name,
                "sale_num": r.sale_num,
                "order_amount": float(r.order_amount) if r.order_amount else 0.0,
                "pay_time": r.pay_time.isoformat() if r.pay_time else None,
                "status": r.status,
                "scraped_at": r.scraped_at.isoformat() if r.scraped_at else None,
            }
            for r in rows
        ]
    }


@router.get("/stats")
async def order_stats(session: AsyncSession = Depends(get_session)) -> dict:
    from sqlalchemy import func
    total = (await session.execute(select(func.count(DoudianOrder.id)))).scalar_one()
    sum_amt = (await session.execute(select(func.sum(DoudianOrder.order_amount)))).scalar_one() or 0
    return {"total_orders": int(total), "total_amount_yuan": float(sum_amt)}
