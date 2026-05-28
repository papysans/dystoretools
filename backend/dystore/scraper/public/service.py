"""Public peer scraping service — orchestrates per-peer fetch + upsert.

Read peer-shop IDs from `app_setting` key `peer_shop_ids` (comma-separated).
Each call: for every configured shop, fetch via DataSource, upsert peer_*.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import text

from dystore.core.logging import get_logger
from dystore.core.settings_store import get as get_setting
from dystore.db.session import SessionLocal
from dystore.scraper.public.datasource import get_datasource
from dystore.ws.broker import publish

log = get_logger(__name__)


async def _record_run(target: str, status: str, items: int, error: str | None = None) -> None:
    async with SessionLocal() as s:
        await s.execute(
            text(
                "INSERT INTO scrape_task_run (target, subsystem, started_at, finished_at, status, items_count, error_msg) "
                "VALUES (:t, 'public', :st, :fn, :s, :c, :e)"
            ),
            {"t": target, "st": datetime.utcnow(), "fn": datetime.utcnow(),
             "s": status, "c": items, "e": (error or "")[:2000] or None},
        )
        await s.commit()


async def _upsert_peer_shop(row: dict) -> None:
    async with SessionLocal() as s:
        await s.execute(
            text(
                "INSERT INTO peer_shop (shop_id, shop_name, follower_count, scraped_at) "
                "VALUES (:shop_id, :shop_name, :follower_count, NOW()) "
                "ON DUPLICATE KEY UPDATE shop_name=VALUES(shop_name), "
                "follower_count=VALUES(follower_count), scraped_at=VALUES(scraped_at)"
            ),
            row,
        )
        await s.commit()


async def run_peer_scrape() -> dict:
    """Iterate configured peer shop ids, fetch shop + goods + livestream, persist."""
    raw = await get_setting("peer_shop_ids") or ""
    shop_ids = [s.strip() for s in raw.split(",") if s.strip()]
    if not shop_ids:
        log.info("public.no_peers_configured")
        await _record_run("peer_shop", "done", 0, "no peer_shop_ids configured")
        return {"shops": 0, "goods": 0, "livestreams": 0}

    ds = get_datasource()
    shops_n = 0
    goods_n = 0
    live_n = 0

    for shop_id in shop_ids:
        try:
            shop_row = await ds.fetch_peer_shop(shop_id)
            if shop_row:
                await _upsert_peer_shop({
                    "shop_id": shop_row.get("shop_id"),
                    "shop_name": shop_row.get("shop_name") or "",
                    "follower_count": shop_row.get("follower_count"),
                })
                shops_n += 1
            goods = await ds.fetch_peer_goods(shop_id)
            goods_n += len(goods)
            lives = await ds.fetch_peer_livestream(shop_id)
            live_n += len(lives)
        except Exception as e:
            log.exception("public.peer_scrape_failed", shop_id=shop_id)
            await _record_run(f"peer_shop[{shop_id}]", "failed", 0, str(e))

    await _record_run("peer_shop", "done", shops_n)
    await _record_run("peer_goods", "done", goods_n)
    await _record_run("peer_livestream", "done", live_n)
    await publish("tasks", {"kind": "task_done", "target": "peer_scrape",
                            "shops": shops_n, "goods": goods_n, "livestreams": live_n})
    return {"shops": shops_n, "goods": goods_n, "livestreams": live_n}
