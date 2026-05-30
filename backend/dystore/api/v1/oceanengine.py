"""千川官方 API 接入路由：OAuth 授权落地、账户同步、报表查询。"""

from datetime import date, timedelta

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dystore.db.models import QianchuanAdvertiser, QianchuanReport
from dystore.db.session import get_session
from dystore.oceanengine import oauth, service

router = APIRouter(prefix="/api/v1/qianchuan", tags=["qianchuan"])


@router.post("/auth/exchange")
async def auth_exchange(auth_code: str = Body(..., embed=True)) -> dict:
    """用 OAuth 回调拿到的 auth_code 换 token 并拉取广告账户。"""
    token = await oauth.exchange_auth_code(auth_code)
    advertisers = await oauth.fetch_advertisers(token)
    return {"uid": token.uid, "advertiser_count": len(advertisers)}


@router.get("/auth/status")
async def auth_status() -> dict:
    return await service.auth_status()


@router.post("/auth/refresh-advertisers")
async def refresh_advertisers() -> dict:
    return {"advertiser_count": await service.refresh_advertiser_list()}


@router.post("/sync")
async def sync(days: int = Body(7, embed=True)) -> dict:
    return await service.sync_all(days=days)


@router.get("/advertisers")
async def advertisers(session: AsyncSession = Depends(get_session)) -> list[dict]:
    rows = (
        (await session.execute(select(QianchuanAdvertiser).order_by(QianchuanAdvertiser.id))).scalars().all()
    )
    return [
        {"advertiser_id": r.advertiser_id, "advertiser_name": r.advertiser_name, "enabled": r.enabled}
        for r in rows
    ]


@router.get("/report")
async def report(
    advertiser_id: str | None = None,
    days: int = Query(30, le=365),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    start = date.today() - timedelta(days=days - 1)
    q = (
        select(QianchuanReport)
        .where(QianchuanReport.level == "advertiser", QianchuanReport.stat_date >= start)
        .order_by(QianchuanReport.stat_date)
    )
    if advertiser_id:
        q = q.where(QianchuanReport.advertiser_id == advertiser_id)
    rows = (await session.execute(q)).scalars().all()
    return [
        {
            "advertiser_id": r.advertiser_id,
            "stat_date": r.stat_date.isoformat(),
            "cost": r.cost,
            "show_cnt": r.show_cnt,
            "click_cnt": r.click_cnt,
            "convert_cnt": r.convert_cnt,
            "convert_cost": r.convert_cost,
            "ctr": r.ctr,
            "pay_order_amount": r.pay_order_amount,
            "roi": r.roi,
        }
        for r in rows
    ]
