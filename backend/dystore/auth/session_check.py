"""Periodic session heartbeat using /ecomauth/loginv1/session_check.

Run by the scheduler at 15-minute intervals during active windows
(07:30–23:59 local time). Treats non-2xx or login-redirected responses as expiry.
"""
import asyncio

from playwright.async_api import BrowserContext

from dystore.auth.events import KIND_SESSION_EXPIRED, emit_session_event
from dystore.core.logging import get_logger

log = get_logger(__name__)

HEARTBEAT_URL = "https://fxg.jinritemai.com/ecomauth/loginv1/session_check"
HEARTBEAT_INTERVAL_SECONDS = 15 * 60


async def heartbeat_once(ctx: BrowserContext) -> bool:
    """Returns True if session is still alive."""
    page = await ctx.new_page()
    try:
        resp = await page.goto(HEARTBEAT_URL, wait_until="load", timeout=15_000)
        ok = bool(resp and resp.ok)
        if not ok or "/login/common" in page.url:
            await emit_session_event(KIND_SESSION_EXPIRED, {"observed_url": page.url, "status": resp.status if resp else None})
            return False
        return True
    except Exception as e:
        log.warning("auth.heartbeat_error", error=str(e))
        return False
    finally:
        await page.close()


async def heartbeat_loop(ctx: BrowserContext, *, cancel: asyncio.Event | None = None) -> None:
    cancel = cancel or asyncio.Event()
    while not cancel.is_set():
        alive = await heartbeat_once(ctx)
        log.info("auth.heartbeat", alive=alive)
        try:
            await asyncio.wait_for(cancel.wait(), timeout=HEARTBEAT_INTERVAL_SECONDS)
        except TimeoutError:
            continue
