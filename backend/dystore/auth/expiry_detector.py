"""URL-based session-expiry detector.

A scraper should call `check_after_navigation(page.url)` after every navigation.
Returns True if the post-nav URL indicates an expired session.
"""
from playwright.async_api import Page

from dystore.auth.events import KIND_SESSION_EXPIRED, emit_session_event


def url_indicates_login(url: str) -> bool:
    return "/login/common" in url


async def check_after_navigation(page: Page, *, expected_path_prefix: str | None = None) -> bool:
    if url_indicates_login(page.url):
        await emit_session_event(KIND_SESSION_EXPIRED, {"observed_url": page.url})
        return True
    if expected_path_prefix and expected_path_prefix not in page.url:
        # navigation landed somewhere unexpected — likely a redirect, treat as suspicious but not expired
        return False
    return False


class SessionExpired(RuntimeError):
    """Raised by scraper engine when a navigation lands on the login page."""
