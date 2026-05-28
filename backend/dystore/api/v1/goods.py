from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dystore.db.models import DoudianGoods
from dystore.db.session import get_session

router = APIRouter(prefix="/api/v1/goods", tags=["goods"])


@router.get("")
async def list_goods(
    tab: str | None = None,
    check_status: int | None = None,
    page: int = 0,
    page_size: int = Query(20, le=200),
    session: AsyncSession = Depends(get_session),
) -> dict:
    filters = []
    if tab is not None:
        filters.append(DoudianGoods.tab == tab)
    if check_status is not None:
        filters.append(DoudianGoods.check_status == check_status)
    total_q = select(func.count(DoudianGoods.id))
    q = (
        select(DoudianGoods)
        .order_by(desc(DoudianGoods.scraped_at), desc(DoudianGoods.id))
        .offset(page * page_size)
        .limit(page_size)
    )
    if filters:
        total_q = total_q.where(*filters)
        q = q.where(*filters)
    total = (await session.execute(total_q)).scalar_one()
    rows = (await session.execute(q)).scalars().all()
    return {
        "total": int(total),
        "items": [
            {
                "goods_id": r.goods_id,
                "title": r.title,
                "price": float(r.price) if r.price else 0.0,
                "stock": r.stock,
                "tab": r.tab,
                "check_status": r.check_status,
                "scraped_at": r.scraped_at.isoformat() if r.scraped_at else None,
            }
            for r in rows
        ],
    }


@router.get("/stats")
async def goods_stats(session: AsyncSession = Depends(get_session)) -> dict:
    total = (await session.execute(select(func.count(DoudianGoods.id)))).scalar_one()
    on_sale = (
        await session.execute(
            select(func.count(DoudianGoods.id)).where(DoudianGoods.tab == "售卖中")
        )
    ).scalar_one()
    low_count = (
        await session.execute(
            select(func.count(DoudianGoods.id)).where(DoudianGoods.stock < 5)
        )
    ).scalar_one()
    return {"total": int(total), "on_sale": int(on_sale), "low_count": int(low_count)}
