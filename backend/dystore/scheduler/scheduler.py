"""APScheduler wiring: 9 daily windows, single-concurrency lock, run-row + WS broadcast."""
import asyncio
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from dystore.auth.persistent_context import merchant_context
from dystore.core.logging import get_logger
from dystore.scheduler.maintenance import drop_old_partitions
from dystore.scraper.antidetect import QuietHoursViolation, assert_not_quiet_hours_for_merchant, is_quiet_hours
from dystore.scraper.engine import run_target
from dystore.scraper.spec_loader import load_all

log = get_logger(__name__)


TZ = "Asia/Shanghai"
WINDOWS = [
    ("0010", CronTrigger(hour=0, minute=10, timezone=TZ)),
    ("0100", CronTrigger(hour=1, minute=0, timezone=TZ)),
    ("0200", CronTrigger(hour=2, minute=0, timezone=TZ)),
    ("0730", CronTrigger(hour=7, minute=30, timezone=TZ)),
    ("1000", CronTrigger(hour=10, minute=0, timezone=TZ)),
    ("1200", CronTrigger(hour=12, minute=0, timezone=TZ)),
    ("1500", CronTrigger(hour=15, minute=0, timezone=TZ)),
    ("1800", CronTrigger(hour=18, minute=0, timezone=TZ)),
    ("2130", CronTrigger(hour=21, minute=30, timezone=TZ)),
]


def _spec_matches_window(spec_cron: str, now: datetime) -> bool:
    """Crude cron-to-now matcher: only checks hour:minute fields.
    Spec cron format: 'min hour day month dow'. We honour min and hour exactly,
    treat day/month/dow as always-true for V1.
    """
    parts = spec_cron.split()
    if len(parts) < 2:
        return False
    minute_part, hour_part = parts[0], parts[1]
    return _matches(minute_part, now.minute) and _matches(hour_part, now.hour)


def _matches(field: str, value: int) -> bool:
    if field == "*":
        return True
    for token in field.split(","):
        if token.startswith("*/"):
            step = int(token[2:])
            if value % step == 0:
                return True
        elif "-" in token:
            lo, hi = token.split("-", 1)
            if int(lo) <= value <= int(hi):
                return True
        elif token.isdigit():
            if int(token) == value:
                return True
    return False


async def _dispatch_window(label: str) -> None:
    now = datetime.now()
    log.info("scheduler.window_fire", label=label)
    if label in ("0100", "0200"):
        # maintenance windows; merchant/public scraping forbidden
        await drop_old_partitions()
        return

    specs = load_all()
    candidates = [s for s in specs.values() if _spec_matches_window(s.schedule.cron, now)]
    if not candidates:
        log.info("scheduler.window_no_candidates", label=label)
        return

    merchant_targets = [s for s in candidates if s.subsystem == "merchant"]
    if merchant_targets:
        if is_quiet_hours(now):
            log.info("scheduler.skip_quiet_hours", label=label, count=len(merchant_targets))
            return
        async with merchant_context() as ctx:
            for spec in merchant_targets:
                try:
                    assert_not_quiet_hours_for_merchant(spec.subsystem)
                    await run_target(spec, ctx)
                except QuietHoursViolation:
                    log.info("scheduler.skip_target_quiet", target=spec.target)
                except Exception:
                    log.exception("scheduler.target_error", target=spec.target)

    # Public/peer scraping fires once per 12:00 window — no merchant cookies leak,
    # no quiet-hours rule (public pages don't have risk-engine on us).
    if label == "1200":
        try:
            from dystore.scraper.public.service import run_peer_scrape
            await run_peer_scrape()
        except Exception:
            log.exception("scheduler.public_peer_failed")


_scheduler: AsyncIOScheduler | None = None


def start_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    _scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
    for label, trigger in WINDOWS:
        _scheduler.add_job(_dispatch_window, trigger, args=[label], id=f"window-{label}", replace_existing=True)
    _scheduler.start()
    log.info("scheduler.started", windows=[w[0] for w in WINDOWS])
    return _scheduler


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None


async def run_target_by_name(target: str) -> dict:
    """Manual dispatch entry. Respects quiet hours + locks via run_target."""
    spec = load_all()[target]
    async with merchant_context() as ctx:
        return await run_target(spec, ctx)
