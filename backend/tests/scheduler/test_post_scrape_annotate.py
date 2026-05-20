"""Tests for post-scrape AI annotation hook in `_dispatch_window`.

Covers the `wire-comment-ai-analysis` OpenSpec change: after merchant comment
scraping targets run, the scheduler must call `annotate_pending(batch_size=50)`,
and the 21:30 window must additionally fire a catch-up
`annotate_pending(batch_size=200)`.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest

from dystore.scheduler import scheduler as scheduler_mod


def _make_spec(target: str, *, subsystem: str = "merchant", cron: str = "* * * * *") -> MagicMock:
    """Build a ScrapeSpec-like mock with the attributes the dispatcher reads."""
    spec = MagicMock()
    spec.target = target
    spec.subsystem = subsystem
    spec.schedule = MagicMock()
    spec.schedule.cron = cron
    return spec


@pytest.fixture
def _patch_scheduler(monkeypatch: pytest.MonkeyPatch) -> dict:
    """Patch all external collaborators of `_dispatch_window` with mocks."""
    fake_ctx = MagicMock(name="merchant_ctx")

    @asynccontextmanager
    async def _merchant_context():
        yield fake_ctx

    annotate_mock = AsyncMock(
        return_value={"ok": 3, "failed": 0, "total": 3, "negative_new": 0}
    )
    run_target_mock = AsyncMock(return_value={"ok": True})
    load_all_mock = MagicMock(return_value={})

    monkeypatch.setattr(scheduler_mod, "load_all", load_all_mock)
    monkeypatch.setattr(scheduler_mod, "merchant_context", _merchant_context)
    monkeypatch.setattr(scheduler_mod, "run_target", run_target_mock)
    monkeypatch.setattr(scheduler_mod, "annotate_pending", annotate_mock)
    monkeypatch.setattr(scheduler_mod, "is_quiet_hours", lambda _now: False)
    monkeypatch.setattr(
        scheduler_mod,
        "assert_not_quiet_hours_for_merchant",
        lambda _subsystem: None,
    )

    return {
        "annotate": annotate_mock,
        "run_target": run_target_mock,
        "load_all": load_all_mock,
    }


async def test_comment_scrape_triggers_annotation(_patch_scheduler: dict) -> None:
    """A `doudian_comment_list` spec running must invoke annotate_pending(batch_size=50)."""
    spec = _make_spec("doudian_comment_list")
    _patch_scheduler["load_all"].return_value = {"doudian_comment_list": spec}

    await scheduler_mod._dispatch_window("1500")

    annotate = _patch_scheduler["annotate"]
    assert annotate.await_count == 1
    annotate.assert_awaited_once_with(batch_size=50)
    _patch_scheduler["run_target"].assert_awaited_once()


async def test_non_comment_scrape_does_not_trigger(_patch_scheduler: dict) -> None:
    """Non-comment merchant targets must NOT trigger the annotation hook."""
    spec = _make_spec("doudian_order")
    _patch_scheduler["load_all"].return_value = {"doudian_order": spec}

    await scheduler_mod._dispatch_window("1500")

    assert _patch_scheduler["annotate"].await_count == 0
    _patch_scheduler["run_target"].assert_awaited_once()


async def test_2130_window_triggers_catchup(_patch_scheduler: dict) -> None:
    """21:30 window fires daily catch-up annotate_pending(batch_size=200) even with no merchant specs.

    A non-merchant candidate is needed to pass the empty-candidates early-return
    while still leaving `merchant_targets` empty so the per-window comment hook
    does NOT fire — isolating the catch-up branch.
    """
    public_spec = _make_spec("public_peer_landing", subsystem="public")
    _patch_scheduler["load_all"].return_value = {"public_peer_landing": public_spec}

    await scheduler_mod._dispatch_window("2130")

    annotate = _patch_scheduler["annotate"]
    assert annotate.await_count >= 1
    catchup_calls = [c for c in annotate.await_args_list if c.kwargs.get("batch_size") == 200]
    assert catchup_calls, (
        f"expected at least one annotate_pending(batch_size=200) call, got {annotate.await_args_list!r}"
    )
