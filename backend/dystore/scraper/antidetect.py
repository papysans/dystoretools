"""Anti-detection rules enforced by the scraper.

- Random per-action delay sampled from U(3, 10) seconds
- Quiet-hours block for merchant subsystem (00:00 - 06:30 local time)
- Single concurrency per (account, domain)
"""
import asyncio
import random
from collections import defaultdict
from datetime import datetime
from urllib.parse import urlparse


def random_delay_seconds() -> float:
    return random.uniform(3.0, 10.0)


async def human_delay() -> None:
    await asyncio.sleep(random_delay_seconds())


def is_quiet_hours(now: datetime | None = None) -> bool:
    """Returns True if current local time is in the 00:00-06:30 merchant-quiet window."""
    now = now or datetime.now()
    if now.hour < 6:
        return True
    if now.hour == 6 and now.minute < 30:
        return True
    return False


class QuietHoursViolation(RuntimeError):
    pass


def assert_not_quiet_hours_for_merchant(subsystem: str, *, now: datetime | None = None) -> None:
    if subsystem == "merchant" and is_quiet_hours(now):
        raise QuietHoursViolation("merchant scrape blocked during 00:00-06:30 quiet hours")


_locks: dict[tuple[str, str], asyncio.Lock] = defaultdict(asyncio.Lock)


def domain_of(url: str) -> str:
    return urlparse(url).netloc


def get_lock(account: str, url: str) -> asyncio.Lock:
    """Single-concurrency lock per (account, domain) tuple."""
    return _locks[(account, domain_of(url))]
