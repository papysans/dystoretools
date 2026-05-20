"""Anonymous Playwright context for public/peer scraping (no merchant cookies).

Uses a fresh Chromium instance per session with playwright-stealth applied.
Separate from `dystore.auth.persistent_context` (which carries merchant login)
to avoid any risk of leaking the merchant identity into public requests.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from playwright.async_api import async_playwright

from dystore.core.config import get_settings
from dystore.core.logging import get_logger

log = get_logger(__name__)


_pw = None
_browser = None
_lock: asyncio.Lock | None = None


async def _ensure_browser():
    global _pw, _browser, _lock
    if _lock is None:
        _lock = asyncio.Lock()
    async with _lock:
        if _browser is not None and _browser.is_connected():
            return _browser
        if _pw is None:
            _pw = await async_playwright().start()
        # Anonymous: no persistent user-data dir → no shared state with merchant session
        _browser = await _pw.chromium.launch(
            headless=get_settings().scraper_headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        log.info("public_context.browser_launched")
        return _browser


@asynccontextmanager
async def public_context():
    """Yield an anonymous BrowserContext with realistic UA + stealth patches."""
    browser = await _ensure_browser()
    ctx = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        locale="zh-CN",
        timezone_id="Asia/Shanghai",
        viewport={"width": 1440, "height": 900},
    )
    # Best-effort stealth — silent fallback if playwright-stealth not installed
    try:
        from playwright_stealth import Stealth
        await Stealth().apply_stealth_async(ctx)
    except Exception as e:
        log.warning("public_context.stealth_unavailable", err=str(e))
    try:
        yield ctx
    finally:
        await ctx.close()


async def shutdown_public_browser() -> None:
    global _pw, _browser
    if _browser:
        try:
            await _browser.close()
        except Exception:
            pass
        _browser = None
    if _pw:
        try:
            await _pw.stop()
        except Exception:
            pass
        _pw = None
