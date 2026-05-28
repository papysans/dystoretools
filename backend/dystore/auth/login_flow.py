"""Manual one-time login flow.

Spec: never automate password entry, OTP retrieval, or risk-verification answers.
We only open a visible browser at the login page and wait for the URL to leave login.
"""
import asyncio

from dystore.auth.events import (
    KIND_LOGIN_SUCCEEDED,
    KIND_RISK_VERIFICATION_REQUIRED,
    KIND_SESSION_READY,
    KIND_SESSION_REQUIRED,
    emit_session_event,
)
from dystore.auth.persistent_context import merchant_context
from dystore.core.logging import get_logger

log = get_logger(__name__)

LOGIN_URL = "https://fxg.jinritemai.com/login/common"
TARGET_HOMEPAGE = "https://fxg.jinritemai.com/ffa/mshop/homepage/index?from=buyin"
LOGIN_TIMEOUT_SECONDS = 10 * 60
RISK_DETECTION_TEXT = "安全验证"


async def open_login_window() -> bool:
    """Open a visible Chromium at the login page, wait until URL leaves login. Returns True on success."""
    await emit_session_event(KIND_SESSION_REQUIRED, {})
    async with merchant_context(headless=False) as ctx:
        page = await ctx.new_page()
        await page.goto(TARGET_HOMEPAGE, wait_until="domcontentloaded")
        risk_seen = False

        deadline = asyncio.get_event_loop().time() + LOGIN_TIMEOUT_SECONDS
        while True:
            if asyncio.get_event_loop().time() > deadline:
                log.warning("auth.login_timeout")
                return False
            try:
                await page.wait_for_url(lambda u: "/login/common" not in u, timeout=3000)
                break
            except Exception:
                # Still on login page — check for risk verification surfacing
                if not risk_seen:
                    content = await page.content()
                    if RISK_DETECTION_TEXT in content:
                        risk_seen = True
                        await emit_session_event(KIND_RISK_VERIFICATION_REQUIRED, {})
                continue

        await emit_session_event(KIND_LOGIN_SUCCEEDED, {"url": page.url})
        await emit_session_event(KIND_SESSION_READY, {})
        return True
