from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dystore.db.models import CommentTagStat, DoudianComment
from dystore.db.session import get_session

router = APIRouter(prefix="/api/v1/comments", tags=["comments"])


@router.get("")
async def list_comments(
    rating: int | None = None,
    sentiment: str | None = None,
    goods_id: str | None = None,
    page: int = 0,
    page_size: int = Query(20, le=200),
    session: AsyncSession = Depends(get_session),
) -> dict:
    filters = []
    if rating is not None:
        filters.append(DoudianComment.rating == rating)
    if sentiment is not None:
        filters.append(DoudianComment.sentiment == sentiment)
    if goods_id is not None:
        filters.append(DoudianComment.goods_id == goods_id)
    q = select(DoudianComment).where(and_(*filters)) if filters else select(DoudianComment)
    q = q.order_by(desc(DoudianComment.id)).offset(page * page_size).limit(page_size)
    rows = (await session.execute(q)).scalars().all()
    return {
        "items": [
            {
                "id": r.id,
                "comment_id": r.comment_id,
                "goods_id": r.goods_id,
                "rating": r.rating,
                "content": r.content,
                "user_nick": r.user_nick,
                "sentiment": r.sentiment,
                "pain_points": (r.pain_points_json or {}).get("tags", []),
                "created_at_src": r.created_at_src.isoformat() if r.created_at_src else None,
            }
            for r in rows
        ]
    }


@router.get("/pain-point/trend")
async def trend(tag: str, days: int = 30, session: AsyncSession = Depends(get_session)) -> dict:
    cutoff = datetime.utcnow() - timedelta(days=days)
    q = (
        select(
            func.date(CommentTagStat.scraped_at).label("d"),
            func.sum(CommentTagStat.neg_count).label("n"),
        )
        .where(CommentTagStat.tag == tag, CommentTagStat.scope == "shop", CommentTagStat.scraped_at >= cutoff)
        .group_by(func.date(CommentTagStat.scraped_at))
        .order_by("d")
    )
    rows = (await session.execute(q)).all()
    return {"tag": tag, "series": [{"date": str(d), "count": int(n)} for d, n in rows]}


@router.get("/pain-point/top")
async def top_pain_points(
    scope: str = "shop", goods_id: str | None = None, limit: int = 20,
    session: AsyncSession = Depends(get_session),
) -> dict:
    filters = [CommentTagStat.scope == scope]
    if goods_id:
        filters.append(CommentTagStat.scope_id == goods_id)
    q = (
        select(CommentTagStat.tag, func.sum(CommentTagStat.neg_count).label("n"))
        .where(*filters)
        .group_by(CommentTagStat.tag)
        .order_by(desc("n"))
        .limit(limit)
    )
    rows = (await session.execute(q)).all()
    return {"items": [{"tag": t, "count": int(n)} for t, n in rows]}
