"""Scraper engine unit tests that do not require a live browser."""
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from dystore.scraper.antidetect import (
    QuietHoursViolation,
    assert_not_quiet_hours_for_merchant,
    domain_of,
    get_lock,
    is_quiet_hours,
)
from dystore.scraper.schema import ScrapeSpec
from dystore.scraper.spec_loader import load_all
from dystore.scraper.telemetry_filter import is_telemetry


def test_specs_load_without_errors() -> None:
    specs = load_all()
    assert "doudian_order" in specs
    spec = specs["doudian_order"]
    assert spec.subsystem == "merchant"
    assert spec.intercept.url_contains == "/api/order/searchlist"
    assert spec.sink.upsert_key == "order_sn"


def test_quiet_hours_block_merchant() -> None:
    assert is_quiet_hours(datetime(2026, 5, 19, 3, 0))
    assert is_quiet_hours(datetime(2026, 5, 19, 6, 29))
    assert not is_quiet_hours(datetime(2026, 5, 19, 6, 30))
    assert not is_quiet_hours(datetime(2026, 5, 19, 12, 0))


def test_assert_not_quiet_hours_raises_for_merchant() -> None:
    with pytest.raises(QuietHoursViolation):
        assert_not_quiet_hours_for_merchant("merchant", now=datetime(2026, 5, 19, 3, 0))


def test_assert_not_quiet_hours_allows_public() -> None:
    # public scraper has no quiet-hours rule
    assert_not_quiet_hours_for_merchant("public", now=datetime(2026, 5, 19, 3, 0))


def test_telemetry_filter() -> None:
    assert is_telemetry("https://mon.zijieapi.com/monitor_browser/collect/batch/")
    assert is_telemetry("https://lf3-config.bytetcc.com/obj/x.json")
    assert is_telemetry("https://lf3-fe.ecombdstatic.com/main.js")
    assert not is_telemetry("https://fxg.jinritemai.com/api/order/searchlist")


def test_domain_lock_keyed_per_account_and_domain() -> None:
    lock_a = get_lock("acct1", "https://fxg.jinritemai.com/x")
    lock_a2 = get_lock("acct1", "https://fxg.jinritemai.com/y")
    lock_b = get_lock("acct2", "https://fxg.jinritemai.com/x")
    assert lock_a is lock_a2  # same account+domain
    assert lock_a is not lock_b  # different account


def test_domain_of() -> None:
    assert domain_of("https://fxg.jinritemai.com/x") == "fxg.jinritemai.com"
