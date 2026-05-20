"""Budget-guard + empty-batch contract tests for comment_worker.annotate_pending.

Boundary mocks only — no real DB, no real LLM:
  * ``dystore.analysis.comment_worker._today_spend_yuan`` for spend value
  * ``dystore.analysis.comment_worker.SessionLocal`` for the pending-rows SELECT
  * ``dystore.analysis.comment_worker.complete`` to assert it is never invoked
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dystore.analysis import comment_worker


def _empty_session_local() -> MagicMock:
    """Build a SessionLocal() async-context-manager mock whose session.execute(...)
    yields a result with .scalars().all() == []  (no pending NULL-sentiment rows)."""
    session = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = []
    exec_result = MagicMock()
    exec_result.scalars.return_value = scalars
    session.execute = AsyncMock(return_value=exec_result)

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)

    session_local = MagicMock(return_value=cm)
    return session_local


@pytest.mark.asyncio
async def test_budget_exhausted_returns_skipped_without_llm_call(monkeypatch):
    monkeypatch.setenv("LLM_DAILY_BUDGET_YUAN", "5")

    with (
        patch.object(comment_worker, "_today_spend_yuan", new=AsyncMock(return_value=10.0)),
        patch.object(comment_worker, "complete", new=AsyncMock()) as mock_complete,
        patch.object(comment_worker, "SessionLocal", new=_empty_session_local()),
    ):
        result = await comment_worker.annotate_pending(batch_size=50)

    assert result["skipped"] == "budget_exhausted"
    assert result["spend_yuan"] == 10.0
    assert result["ok"] == 0
    assert result["failed"] == 0
    assert result["total"] == 0
    mock_complete.assert_not_called()


@pytest.mark.asyncio
async def test_no_pending_returns_no_pending(monkeypatch):
    monkeypatch.setenv("LLM_DAILY_BUDGET_YUAN", "5")

    with (
        patch.object(comment_worker, "_today_spend_yuan", new=AsyncMock(return_value=0.0)),
        patch.object(comment_worker, "complete", new=AsyncMock()) as mock_complete,
        patch.object(comment_worker, "SessionLocal", new=_empty_session_local()),
    ):
        result = await comment_worker.annotate_pending(batch_size=50)

    assert result == {"ok": 0, "failed": 0, "total": 0, "skipped": "no_pending"}
    mock_complete.assert_not_called()


@pytest.mark.asyncio
async def test_structured_summary_contract(monkeypatch):
    monkeypatch.setenv("LLM_DAILY_BUDGET_YUAN", "5")

    with (
        patch.object(comment_worker, "_today_spend_yuan", new=AsyncMock(return_value=0.0)),
        patch.object(comment_worker, "complete", new=AsyncMock()),
        patch.object(comment_worker, "SessionLocal", new=_empty_session_local()),
    ):
        result = await comment_worker.annotate_pending(batch_size=50)

    assert set(result.keys()) >= {"ok", "failed", "total"}
