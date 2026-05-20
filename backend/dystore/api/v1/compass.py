from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from dystore.db.models import (
    CompassCoreData,
    CompassCoreTrend,
    CompassDiagnose,
    CompassIndustryWord,
    CompassShopRank,
    ShopVideo,
)
from dystore.db.session import get_session

router = APIRouter(prefix="/api/v1/compass", tags=["compass"])


@router.get("/core")
async def core_data(limit: int = Query(100, le=500), session: AsyncSession = Depends(get_session)) -> list[dict]:
    rows = (await session.execute(select(CompassCoreData).order_by(desc(CompassCoreData.id)).limit(limit))).scalars().all()
    return [{"id": r.id, "scope": r.scope, "metric": r.metric, "value": r.value, "scraped_at": r.scraped_at.isoformat()} for r in rows]


@router.get("/trend")
async def core_trend(index_name: str, limit: int = Query(180, le=730), session: AsyncSession = Depends(get_session)) -> list[dict]:
    rows = (
        await session.execute(
            select(CompassCoreTrend).where(CompassCoreTrend.index_name == index_name).order_by(CompassCoreTrend.date).limit(limit)
        )
    ).scalars().all()
    return [{"date": r.date.isoformat(), "value": r.value} for r in rows]


@router.get("/diagnose")
async def diagnose(limit: int = 50, session: AsyncSession = Depends(get_session)) -> list[dict]:
    rows = (await session.execute(select(CompassDiagnose).order_by(desc(CompassDiagnose.id)).limit(limit))).scalars().all()
    return [{"id": r.id, "kind": r.kind, "payload": r.payload_json, "scraped_at": r.scraped_at.isoformat()} for r in rows]


@router.get("/industry-word")
async def industry_word(rank_type: int | None = None, limit: int = Query(50, le=500), session: AsyncSession = Depends(get_session)) -> list[dict]:
    q = select(CompassIndustryWord).order_by(desc(CompassIndustryWord.scraped_at), CompassIndustryWord.rank).limit(limit)
    if rank_type is not None:
        q = q.where(CompassIndustryWord.rank_type == rank_type)
    rows = (await session.execute(q)).scalars().all()
    return [{"word": r.word, "rank": r.rank, "value": r.value, "rank_type": r.rank_type, "scraped_at": r.scraped_at.isoformat()} for r in rows]


@router.get("/shop-rank")
async def shop_rank(sort_field: str = "pay_amt", session: AsyncSession = Depends(get_session)) -> list[dict]:
    rows = (
        await session.execute(
            select(CompassShopRank).where(CompassShopRank.sort_field == sort_field).order_by(desc(CompassShopRank.scraped_at)).limit(30)
        )
    ).scalars().all()
    return [{"rank": r.rank, "value": r.value, "scraped_at": r.scraped_at.isoformat()} for r in rows]


@router.get("/videos")
async def videos(limit: int = Query(50, le=500), session: AsyncSession = Depends(get_session)) -> list[dict]:
    rows = (await session.execute(select(ShopVideo).order_by(desc(ShopVideo.publish_at)).limit(limit))).scalars().all()
    return [
        {
            "video_id": r.video_id,
            "play_count": r.play_count,
            "gmv": r.gmv,
            "publish_at": r.publish_at.isoformat() if r.publish_at else None,
            "audit_status": r.audit_status,
        }
        for r in rows
    ]
