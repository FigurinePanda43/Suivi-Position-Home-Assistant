"""Unit tests for date / duration helpers (no Home Assistant instance needed)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from homeassistant.util import dt as dt_util
import pytest

from custom_components.suivi_presence.util import (
    format_duration_hms,
    format_timestamp,
    parse_duration_seconds,
    parse_timestamp,
    parse_user_datetime,
)

PARIS = ZoneInfo("Europe/Paris")


@pytest.fixture(autouse=True)
def paris_timezone():
    """Run every test with Europe/Paris as the Home Assistant time zone."""
    previous = dt_util.DEFAULT_TIME_ZONE
    dt_util.set_default_time_zone(PARIS)
    yield
    dt_util.set_default_time_zone(previous)


def test_parse_timestamp_legacy_utc_and_new_local_are_equivalent() -> None:
    """Rows written by 0.1.x (UTC) and 1.0.0 (local + offset) parse to the same instant."""
    legacy = parse_timestamp("2025-09-01T08:30:00.123456+00:00")
    new = parse_timestamp("2025-09-01T10:30:00+02:00")
    assert legacy is not None and new is not None
    assert legacy.replace(microsecond=0) == new
    assert new.tzinfo is not None


def test_parse_timestamp_naive_is_local_time() -> None:
    parsed = parse_timestamp("2025-09-01T10:30:00")
    assert parsed == datetime(2025, 9, 1, 8, 30, tzinfo=UTC)


def test_parse_timestamp_invalid() -> None:
    assert parse_timestamp("") is None
    assert parse_timestamp(None) is None
    assert parse_timestamp("not a date") is None


def test_format_timestamp_is_local_with_offset_and_no_microseconds() -> None:
    value = datetime(2025, 9, 1, 8, 30, 15, 999999, tzinfo=UTC)
    assert format_timestamp(value) == "2025-09-01T10:30:15+02:00"


def test_parse_user_datetime_date_bounds() -> None:
    start = parse_user_datetime("2025-09-01")
    end = parse_user_datetime("2025-09-01", end_of_day=True)
    assert start == datetime(2025, 8, 31, 22, 0, tzinfo=UTC)  # midnight Paris (CEST)
    assert end is not None and end.date() == datetime(2025, 9, 1, tzinfo=UTC).date()
    assert end - start == timedelta(days=1) - timedelta(microseconds=1)


def test_parse_user_datetime_naive_datetime_and_iso() -> None:
    naive = parse_user_datetime("2025-09-01T00:00:00")
    assert naive == datetime(2025, 8, 31, 22, 0, tzinfo=UTC)
    aware = parse_user_datetime("2025-09-01T00:00:00+00:00")
    assert aware == datetime(2025, 9, 1, 0, 0, tzinfo=UTC)
    assert parse_user_datetime("") is None
    assert parse_user_datetime(None) is None
    assert parse_user_datetime("31/12/2025") is None


@pytest.mark.parametrize(
    ("record", "expected"),
    [
        ({"duration_seconds": "45000"}, 45000.0),
        ({"duration_seconds": "45000.123456"}, 45000.123456),
        ({"duration_seconds": "", "duration_in_previous": "26:03:04"}, 26 * 3600 + 3 * 60 + 4),
        ({"duration_in_previous": "1 day, 2:03:04.567890"}, 86400 + 2 * 3600 + 3 * 60 + 4.56789),
        ({"duration_in_previous": "2 days, 0:00:01"}, 2 * 86400 + 1),
        ({"duration_in_previous": "0:00:00.001014"}, 0.001014),
        ({"duration_in_previous": ""}, None),
        ({}, None),
        ({"duration_in_previous": "garbage"}, None),
        ({"duration_seconds": "-5"}, None),
    ],
)
def test_parse_duration_seconds(record: dict, expected: float | None) -> None:
    result = parse_duration_seconds(record)
    if expected is None:
        assert result is None
    else:
        assert result == pytest.approx(expected)


def test_format_duration_hms() -> None:
    assert format_duration_hms(0) == "0:00:00"
    assert format_duration_hms(59.6) == "0:01:00"
    assert format_duration_hms(26 * 3600 + 3 * 60 + 4) == "26:03:04"
    assert format_duration_hms(None) == ""
    assert format_duration_hms(-1) == ""
