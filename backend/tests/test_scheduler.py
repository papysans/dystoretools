from datetime import datetime

from dystore.scheduler.scheduler import _matches, _spec_matches_window


def test_matches_star() -> None:
    assert _matches("*", 5)
    assert _matches("*", 0)


def test_matches_digit() -> None:
    assert _matches("10", 10)
    assert not _matches("10", 11)


def test_matches_list() -> None:
    assert _matches("0,7,10,12,15,18,21", 12)
    assert not _matches("0,7,10,12,15,18,21", 13)


def test_matches_range() -> None:
    assert _matches("7-22", 10)
    assert not _matches("7-22", 6)


def test_matches_step() -> None:
    assert _matches("*/30", 0)
    assert _matches("*/30", 30)
    assert not _matches("*/30", 31)


def test_spec_window() -> None:
    assert _spec_matches_window("10 12 * * *", datetime(2026, 5, 19, 12, 10))
    assert not _spec_matches_window("10 12 * * *", datetime(2026, 5, 19, 12, 11))
    assert _spec_matches_window("10 0,7,10,12,15,18,21 * * *", datetime(2026, 5, 19, 18, 10))
