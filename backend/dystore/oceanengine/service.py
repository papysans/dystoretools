"""千川同步编排：遍历已授权广告账户拉取报表，记录 scrape_task_run 生命周期 + WS 广播。"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select, text

from dystore.core.logging import get_logger
from dystore.db.models import QianchuanAdvertiser, QianchuanToken
from dystore.db.session import SessionLocal
from dystore.oceanengine.oauth import fetch_advertisers, get_valid_access_token
from dystore.oceanengine.report import fetch_advertiser_report
from dystore.ws.broker import publish

log = get_logger(__name__)


async def _record_run(target: str, status: str, items: int, error: str | None = None) -> None:
    async with SessionLocal() as s:
        await s.execute(
            text(
                "INSERT INTO scrape_task_run (target, subsystem, started_at, finished_at, status, items_count, error_msg) "
                "VALUES (:t, 'oceanengine', :st, :fn, :s, :c, :e)"
            ),
            {
                "t": target,
                "st": datetime.utcnow(),
                "fn": datetime.utcnow(),
                "s": status,
                "c": items,
                "e": (error or "")[:2000] or None,
            },
        )
        await s.commit()


async def sync_all(days: int = 7) -> dict:
    """同步全部已启用广告账户最近 days 天报表。"""
    today = datetime.utcnow().date()
    start = today - timedelta(days=days - 1)

    async with SessionLocal() as s:
        advertisers = (
            (await s.execute(select(QianchuanAdvertiser).where(QianchuanAdvertiser.enabled.is_(True))))
            .scalars()
            .all()
        )

    if not advertisers:
        await _record_run("qianchuan_report", "done", 0, "no authorized advertisers")
        return {"advertisers": 0, "rows": 0}

    total_rows = 0
    failed = 0
    for adv in advertisers:
        try:
            total_rows += await fetch_advertiser_report(adv.advertiser_id, start, today)
        except Exception as e:
            failed += 1
            log.exception("qianchuan.sync_failed", advertiser_id=adv.advertiser_id)
            await _record_run(f"qianchuan_report[{adv.advertiser_id}]", "failed", 0, str(e))

    status = "done" if failed == 0 else "partial"
    await _record_run("qianchuan_report", status, total_rows)
    await publish(
        "tasks",
        {
            "kind": "task_done",
            "target": "qianchuan_sync",
            "advertisers": len(advertisers),
            "rows": total_rows,
            "failed": failed,
        },
    )
    return {"advertisers": len(advertisers), "rows": total_rows, "failed": failed}


async def refresh_advertiser_list() -> int:
    """重新拉取首个授权下的广告账户清单。"""
    async with SessionLocal() as s:
        token = (await s.execute(select(QianchuanToken).order_by(QianchuanToken.id))).scalars().first()
    if token is None:
        raise RuntimeError("尚未授权")
    # 触发一次有效性检查（必要时刷新）
    await get_valid_access_token(token.uid)
    items = await fetch_advertisers(token)
    return len(items)


async def auth_status() -> dict:
    async with SessionLocal() as s:
        token = (await s.execute(select(QianchuanToken).order_by(QianchuanToken.id))).scalars().first()
        adv_count = len((await s.execute(select(QianchuanAdvertiser))).scalars().all())
    return {
        "authorized": token is not None,
        "uid": token.uid if token else None,
        "access_expires_at": token.access_expires_at.isoformat() if token else None,
        "refresh_expires_at": token.refresh_expires_at.isoformat()
        if token and token.refresh_expires_at
        else None,
        "advertiser_count": adv_count,
    }
