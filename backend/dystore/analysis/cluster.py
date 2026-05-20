"""21:30 clustering job: tag frequency over the past 30 days."""
from collections import Counter
from datetime import datetime, timedelta

from sqlalchemy import select

from dystore.core.logging import get_logger
from dystore.db.models import CommentTagStat, DoudianComment
from dystore.db.session import SessionLocal

log = get_logger(__name__)


async def run_clustering(*, lookback_days: int = 30, min_count: int = 3) -> dict:
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)
    async with SessionLocal() as s:
        rows = (
            await s.execute(
                select(DoudianComment.goods_id, DoudianComment.pain_points_json)
                .where(DoudianComment.scraped_at >= cutoff)
                .where(DoudianComment.pain_points_json.is_not(None))
            )
        ).all()

    shop_counter: Counter[str] = Counter()
    shop_total: Counter[str] = Counter()
    goods_counter: dict[str, Counter[str]] = {}
    goods_total: dict[str, int] = {}

    for goods_id, pp in rows:
        tags = (pp or {}).get("tags", [])
        if not tags:
            continue
        shop_total["__shop__"] += 1
        if goods_id:
            goods_total[goods_id] = goods_total.get(goods_id, 0) + 1
        for t in tags:
            tag = t.get("tag") if isinstance(t, dict) else None
            if not tag:
                continue
            shop_counter[tag] += 1
            if goods_id:
                goods_counter.setdefault(goods_id, Counter())[tag] += 1

    inserted = 0
    async with SessionLocal() as s:
        for tag, neg in shop_counter.items():
            if neg < min_count:
                continue
            s.add(
                CommentTagStat(
                    scope="shop",
                    scope_id=None,
                    tag=tag,
                    neg_count=neg,
                    total_count=shop_total["__shop__"],
                )
            )
            inserted += 1
        for goods_id, ctr in goods_counter.items():
            for tag, neg in ctr.items():
                if neg < min_count:
                    continue
                s.add(
                    CommentTagStat(
                        scope="goods",
                        scope_id=goods_id,
                        tag=tag,
                        neg_count=neg,
                        total_count=goods_total[goods_id],
                    )
                )
                inserted += 1
        await s.commit()
    log.info("analysis.clustering_done", inserted=inserted, lookback_days=lookback_days)
    return {"inserted": inserted}
