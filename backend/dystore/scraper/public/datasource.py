"""Pluggable backend for V2 peer scraping.

The default `PlaywrightDataSource` drives anonymous headless Chromium against
抖音/抖店 public pages. Two stub alternatives demonstrate the interface for
3rd-party data APIs (灰豚 / 蝉妈妈) — they are not wired by default.

Selection happens via env var `PUBLIC_SCRAPER_BACKEND` ∈ {playwright, huitu, chanmama}.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from dystore.core.config import get_settings
from dystore.core.logging import get_logger

log = get_logger(__name__)


class DataSource(ABC):
    @abstractmethod
    async def fetch_peer_shop(self, shop_id: str) -> dict: ...
    @abstractmethod
    async def fetch_peer_goods(self, shop_id: str, *, limit: int = 50) -> list[dict]: ...
    @abstractmethod
    async def fetch_peer_livestream(self, shop_id: str, *, lookback_days: int = 7) -> list[dict]: ...


class PlaywrightDataSource(DataSource):
    """Anonymous Playwright-based peer scraping.

    Targets the public-facing shop pages at haohuo.jinritemai.com (mobile-style
    product hubs) plus live.douyin.com for broadcast schedules. Returns whatever
    can be parsed from the public render; partial data is fine.
    """

    async def fetch_peer_shop(self, shop_id: str) -> dict:
        from dystore.scraper.public.public_context import public_context
        url = f"https://haohuo.jinritemai.com/ecommerce/trade/detail/index.html?shop_id={shop_id}"
        async with public_context() as ctx:
            page = await ctx.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                await page.wait_for_timeout(2000)
                title = await page.title()
                # Best-effort scrape: read og:* metadata + visible shop name node
                meta = await page.evaluate("""() => ({
                    og_title: document.querySelector('meta[property=\"og:title\"]')?.content || null,
                    og_description: document.querySelector('meta[property=\"og:description\"]')?.content || null,
                    shop_name_text: document.querySelector('[class*=\"shop\"][class*=\"name\"]')?.innerText || null
                })""")
                log.info("public.peer_shop_fetched", shop_id=shop_id, title=title[:50])
                return {
                    "shop_id": shop_id,
                    "shop_name": meta.get("og_title") or meta.get("shop_name_text") or title,
                    "follower_count": None,  # not exposed in public render
                    "raw": meta,
                }
            finally:
                await page.close()

    async def fetch_peer_goods(self, shop_id: str, *, limit: int = 50) -> list[dict]:
        # Public shop goods list endpoint requires page-specific recon — TODO once
        # we have an actual peer shop URL to recon. Currently returns empty.
        log.info("public.peer_goods_recon_needed", shop_id=shop_id)
        return []

    async def fetch_peer_livestream(self, shop_id: str, *, lookback_days: int = 7) -> list[dict]:
        # live.douyin.com room data needs WSS interception — V2 P0 follow-up.
        log.info("public.peer_livestream_recon_needed", shop_id=shop_id, days=lookback_days)
        return []


class HuituDataSource(DataSource):
    async def fetch_peer_shop(self, shop_id: str) -> dict:
        if not get_settings().huitu_api_key:
            raise RuntimeError("HUITU_API_KEY missing in .env")
        raise NotImplementedError("huitu backend stub")

    async def fetch_peer_goods(self, shop_id: str, *, limit: int = 50) -> list[dict]:
        raise NotImplementedError("huitu backend stub")

    async def fetch_peer_livestream(self, shop_id: str, *, lookback_days: int = 7) -> list[dict]:
        raise NotImplementedError("huitu backend stub")


class ChanMamaDataSource(DataSource):
    async def fetch_peer_shop(self, shop_id: str) -> dict:
        if not get_settings().chanmama_api_key:
            raise RuntimeError("CHANMAMA_API_KEY missing in .env")
        raise NotImplementedError("chanmama backend stub")

    async def fetch_peer_goods(self, shop_id: str, *, limit: int = 50) -> list[dict]:
        raise NotImplementedError("chanmama backend stub")

    async def fetch_peer_livestream(self, shop_id: str, *, lookback_days: int = 7) -> list[dict]:
        raise NotImplementedError("chanmama backend stub")


def get_datasource() -> DataSource:
    backend = get_settings().public_scraper_backend
    if backend == "huitu":
        return HuituDataSource()
    if backend == "chanmama":
        return ChanMamaDataSource()
    return PlaywrightDataSource()
