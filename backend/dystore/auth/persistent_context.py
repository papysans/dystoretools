"""Playwright Chromium contexts for merchant and public scrapers.

Two modes for the merchant context (set via settings `merchant_browser_mode`):
- "playwright": launch headless Chromium inside the container — fast, but the bytedance
  risk engine consistently flags this fingerprint as automation.
- "cdp": connect via Chrome DevTools Protocol to a real Google Chrome running on the
  host. Real fingerprint, real IP, real cookies — risk engine doesn't flag it.

Host Chrome launch (one-time):
  Windows:  & "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" `
              --remote-debugging-port=9222 `
              --user-data-dir="$env:USERPROFILE\\.dystore-chrome"
  macOS:    /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \
              --remote-debugging-port=9222 \
              --user-data-dir="$HOME/.dystore-chrome"
  Then log in to fxg.jinritemai.com inside that Chrome once.
"""
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import httpx
from playwright.async_api import BrowserContext, async_playwright

try:
    from playwright_stealth import Stealth
    _STEALTH_OK = True
    _STEALTH_ERR: Exception | None = None
except ImportError as e:
    Stealth = None  # type: ignore[assignment]
    _STEALTH_OK = False
    _STEALTH_ERR = e

from dystore.core.config import get_settings
from dystore.core.logging import get_logger
from dystore.core.settings_store import get as get_setting

log = get_logger(__name__)

ContextName = Literal["doudian", "public"]


def _user_data_dir(name: ContextName) -> Path:
    base = get_settings().playwright_user_data_dir
    p = base / name
    p.mkdir(parents=True, exist_ok=True)
    return p


def require_stealth() -> None:
    if not _STEALTH_OK:
        raise RuntimeError(f"playwright-stealth import failed: {_STEALTH_ERR}")


async def _apply_stealth(ctx: BrowserContext) -> None:
    if _STEALTH_OK and Stealth is not None:
        await Stealth().apply_stealth_async(ctx)


async def _resolve_cdp_ws_url(http_url: str, *, timeout: float = 5.0) -> str:
    """Chrome 111+ rejects WS upgrade requests whose Host header isn't an IP/localhost.
    Resolve any hostname to its IP first so the Host header becomes an IP (always accepted),
    then fetch /json/version (override Host to localhost for the HTTP probe) and substitute
    in the WS URL.

    Chrome must be launched with `--remote-debugging-address=0.0.0.0 --remote-allow-origins=*`
    for connections from a non-loopback IP to work.
    """
    import socket
    from urllib.parse import urlparse
    parsed = urlparse(http_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 9222
    # Resolve hostname → IP so Host header is acceptable
    try:
        host_ip = socket.gethostbyname(host)
    except socket.gaierror:
        host_ip = host
    probe_url = f"http://{host_ip}:{port}"
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.get(f"{probe_url}/json/version", headers={"Host": f"localhost:{port}"})
        r.raise_for_status()
        data = r.json()
    ws_url = data.get("webSocketDebuggerUrl") or probe_url
    for needle in ("127.0.0.1", "localhost"):
        if f"://{needle}:" in ws_url:
            ws_url = ws_url.replace(f"://{needle}:", f"://{host_ip}:", 1)
            break
    return ws_url


@asynccontextmanager
async def _playwright_local_merchant_context(*, headless: bool):
    require_stealth()
    async with async_playwright() as pw:
        kwargs = dict(
            user_data_dir=str(_user_data_dir("doudian")),
            headless=headless,
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            viewport={"width": 1440, "height": 900},
        )
        try:
            ctx: BrowserContext = await pw.chromium.launch_persistent_context(channel="chrome", **kwargs)  # type: ignore[arg-type]
            log.info("auth.merchant_context_open", mode="playwright", channel="chrome", headless=headless)
        except Exception as e:
            log.warning("auth.chrome_channel_unavailable", error=str(e))
            ctx = await pw.chromium.launch_persistent_context(**kwargs)  # type: ignore[arg-type]
            log.info("auth.merchant_context_open", mode="playwright", channel="bundled-chromium", headless=headless)
        await _apply_stealth(ctx)
        try:
            yield ctx
        finally:
            await ctx.close()
            log.info("auth.merchant_context_closed", mode="playwright")


# Singleton CDP state — one Playwright + one Browser shared across all merchant scrapes.
# Rationale: each connect_over_cdp/pw.stop cycle disrupts Chrome's context handle, causing
# subsequent scrapes to see "TargetClosedError" on new_page. Keeping a long-lived connection
# avoids the churn entirely.
_cdp_pw = None
_cdp_browser = None
_cdp_lock = None
_cdp_stealth_applied = False


async def _ensure_cdp_browser():
    global _cdp_pw, _cdp_browser, _cdp_lock
    import asyncio
    if _cdp_lock is None:
        _cdp_lock = asyncio.Lock()
    async with _cdp_lock:
        if _cdp_browser is not None and _cdp_browser.is_connected():
            return _cdp_browser
        # (Re)connect
        cdp_url = await get_setting("merchant_cdp_url") or get_settings().merchant_cdp_url
        ws_url = await _resolve_cdp_ws_url(cdp_url)
        if _cdp_pw is None:
            _cdp_pw = await async_playwright().start()
        _cdp_browser = await _cdp_pw.chromium.connect_over_cdp(ws_url)
        log.info("auth.cdp_browser_connected", cdp_url=cdp_url)
        return _cdp_browser


@asynccontextmanager
async def _cdp_merchant_context():
    """Connect to host Chrome via CDP. Reuses a singleton Browser handle across scrapes."""
    require_stealth()
    global _cdp_stealth_applied
    try:
        browser = await _ensure_cdp_browser()
    except Exception as e:
        raise RuntimeError(
            f"无法连到 host Chrome. 请确认 host Chrome 已用 --remote-debugging-port=9222 启动. 原因: {e}"
        ) from e
    contexts = browser.contexts
    if not contexts:
        ctx = await browser.new_context(locale="zh-CN", timezone_id="Asia/Shanghai")
    else:
        ctx = contexts[0]
    if not _cdp_stealth_applied:
        await _apply_stealth(ctx)
        _cdp_stealth_applied = True
    log.info("auth.merchant_context_open", mode="cdp", existing_pages=len(ctx.pages))
    try:
        yield ctx
    finally:
        # Do NOT close ctx, do NOT close browser, do NOT stop playwright.
        # The singleton stays alive for the next scrape.
        log.info("auth.merchant_context_released", mode="cdp")


@asynccontextmanager
async def merchant_context(*, headless: bool | None = None):
    """Dispatch on settings.merchant_browser_mode."""
    mode = await get_setting("merchant_browser_mode") or get_settings().merchant_browser_mode
    if mode == "cdp":
        async with _cdp_merchant_context() as ctx:
            yield ctx
    else:
        if headless is None:
            headless = get_settings().scraper_headless
        async with _playwright_local_merchant_context(headless=headless) as ctx:
            yield ctx


@asynccontextmanager
async def public_context():
    """Public scraper always uses local Chromium — no need to touch host Chrome."""
    require_stealth()
    async with async_playwright() as pw:
        kwargs = dict(
            user_data_dir=str(_user_data_dir("public")),
            headless=True,
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            viewport={"width": 1280, "height": 800},
        )
        try:
            ctx = await pw.chromium.launch_persistent_context(channel="chrome", **kwargs)  # type: ignore[arg-type]
        except Exception:
            ctx = await pw.chromium.launch_persistent_context(**kwargs)  # type: ignore[arg-type]
        await _apply_stealth(ctx)
        log.info("auth.public_context_open")
        try:
            yield ctx
        finally:
            await ctx.close()
