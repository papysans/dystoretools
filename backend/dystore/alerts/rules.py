"""Alert rules. Each function reads recent data and may fire one or more alerts."""
import statistics
from datetime import datetime, timedelta

from sqlalchemy import func, select

from dystore.alerts.dispatcher import fire
from dystore.db.models import AftersaleCounts, DoudianComment, DoudianOrder, DoudianSkuDiagnose, PeerGoods, PeerLivestream
from dystore.db.session import SessionLocal

NEGATIVE_SURGE_WINDOW_MINUTES = 60
NEGATIVE_SURGE_THRESHOLD = 5

URGE_DIM = "urge_audit"
DEADLINE_DIM = "approaching_deadline_audit"
ARBITRATE_DIMS = ("arbitrate_pending", "arbitrate_pending_evidence", "arbitrate_pending_negotiation")

SALES_LOOKBACK_DAYS = 7
SALES_MAD_K = 3.0


async def run_negative_comment_surge() -> int:
    cutoff = datetime.utcnow() - timedelta(minutes=NEGATIVE_SURGE_WINDOW_MINUTES)
    async with SessionLocal() as s:
        rows = (
            await s.execute(
                select(DoudianComment.goods_id, func.count())
                .where(DoudianComment.sentiment == "negative", DoudianComment.scraped_at >= cutoff)
                .group_by(DoudianComment.goods_id)
            )
        ).all()
    fired = 0
    for goods_id, count in rows:
        if count >= NEGATIVE_SURGE_THRESHOLD:
            await fire("negative_comment_surge", "warn", {"goods_id": goods_id, "count": int(count)})
            fired += 1
    return fired


async def run_aftersale_alerts() -> int:
    async with SessionLocal() as s:
        rows = (
            await s.execute(
                select(AftersaleCounts.dim, func.max(AftersaleCounts.count))
                .where(AftersaleCounts.scraped_at >= datetime.utcnow() - timedelta(hours=2))
                .group_by(AftersaleCounts.dim)
            )
        ).all()
    fired = 0
    for dim, count in rows:
        if count == 0:
            continue
        if dim == DEADLINE_DIM:
            await fire("aftersale_deadline_approaching", "critical", {"dim": dim, "count": int(count)})
            fired += 1
        elif dim == URGE_DIM:
            await fire("aftersale_urge", "warn", {"dim": dim, "count": int(count)})
            fired += 1
        elif dim in ARBITRATE_DIMS:
            await fire("aftersale_arbitrate_pending", "critical", {"dim": dim, "count": int(count)})
            fired += 1
    return fired


async def run_stock_alerts() -> int:
    async with SessionLocal() as s:
        rows = (
            await s.execute(
                select(DoudianSkuDiagnose).where(
                    DoudianSkuDiagnose.scraped_at >= datetime.utcnow() - timedelta(hours=12)
                )
            )
        ).scalars().all()
    fired = 0
    for r in rows:
        if r.diagnose_type in ("low_stock", "out_of_stock"):
            await fire("low_stock", "warn", {"goods_id": r.goods_id, "sku_id": r.sku_id, "type": r.diagnose_type})
            fired += 1
        elif r.diagnose_type == "dead_stock":
            await fire("dead_stock", "info", {"goods_id": r.goods_id, "sku_id": r.sku_id})
            fired += 1
    return fired


async def run_sales_anomaly() -> int:
    """Compare last hour's order count vs median of same hour-of-day in last 7 days."""
    now = datetime.utcnow()
    hour_start = now.replace(minute=0, second=0, microsecond=0)
    last_hour_start = hour_start - timedelta(hours=1)
    async with SessionLocal() as s:
        observed = (
            await s.execute(
                select(func.count()).where(DoudianOrder.pay_time >= last_hour_start, DoudianOrder.pay_time < hour_start)
            )
        ).scalar_one()
        history: list[int] = []
        for d in range(1, SALES_LOOKBACK_DAYS + 1):
            ws = last_hour_start - timedelta(days=d)
            we = hour_start - timedelta(days=d)
            cnt = (await s.execute(select(func.count()).where(DoudianOrder.pay_time >= ws, DoudianOrder.pay_time < we))).scalar_one()
            history.append(cnt)
    if len(history) < 5:
        return 0
    med = statistics.median(history)
    mad = statistics.median([abs(x - med) for x in history]) or 1.0
    z = (observed - med) / mad
    if z <= -SALES_MAD_K:
        await fire("sales_anomaly_drop", "warn", {"observed": int(observed), "expected": med, "z": z})
        return 1
    if z >= SALES_MAD_K:
        await fire("sales_anomaly_spike", "info", {"observed": int(observed), "expected": med, "z": z})
        return 1
    return 0


async def run_peer_anomaly() -> int:
    """Flag notable peer changes — new live broadcast started in last hour, or
    a peer goods price changed >20% since the prior snapshot."""
    fired = 0
    cutoff = datetime.utcnow() - timedelta(hours=1)
    async with SessionLocal() as s:
        recent_live = (
            await s.execute(
                select(PeerLivestream.peer_shop_id, func.count())
                .where(PeerLivestream.start_time >= cutoff)
                .group_by(PeerLivestream.peer_shop_id)
            )
        ).all()
    for peer_shop_id, n in recent_live:
        if n:
            await fire("peer_livestream_started", "info",
                       {"peer_shop_id": peer_shop_id, "starts_last_hour": int(n)})
            fired += 1

    async with SessionLocal() as s:
        # Detect price drift: for each peer goods, compare latest 2 snapshots
        latest_two = (
            await s.execute(
                select(PeerGoods.peer_shop_id, PeerGoods.goods_id, PeerGoods.peer_price, PeerGoods.scraped_at)
                .order_by(PeerGoods.peer_shop_id, PeerGoods.goods_id, PeerGoods.scraped_at.desc())
                .limit(2000)
            )
        ).all()
    by_key: dict[tuple[str, str], list[tuple]] = {}
    for shop_id, goods_id, price, ts in latest_two:
        by_key.setdefault((shop_id, goods_id), []).append((price, ts))
    for (shop_id, goods_id), snaps in by_key.items():
        if len(snaps) < 2:
            continue
        new_p, _ = snaps[0]
        old_p, _ = snaps[1]
        if not (new_p and old_p):
            continue
        try:
            drift = abs(float(new_p) - float(old_p)) / float(old_p)
        except (TypeError, ZeroDivisionError):
            continue
        if drift >= 0.2:
            await fire("peer_price_shift", "warn",
                       {"peer_shop_id": shop_id, "goods_id": goods_id,
                        "new_price": float(new_p), "old_price": float(old_p),
                        "drift_pct": round(drift * 100, 1)})
            fired += 1
    return fired


async def run_all_after_scrape() -> dict:
    return {
        "negative_comment_surge": await run_negative_comment_surge(),
        "aftersale": await run_aftersale_alerts(),
        "stock": await run_stock_alerts(),
        "sales_anomaly": await run_sales_anomaly(),
        "peer_anomaly": await run_peer_anomaly(),
    }
