"""Unit tests for the interval based zone statistics."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from custom_components.suivi_presence.stats import (
    CurrentState,
    history_date_range,
    summary_as_dict,
    zone_summary,
)

T0 = datetime(2025, 9, 1, 0, 0, tzinfo=UTC)


def _rec(
    ts: datetime, person: str, prev: str, new: str, seconds: float | None, entity: str = ""
) -> dict:
    return {
        "timestamp": ts.isoformat(),
        "person": person,
        "previous_zone": prev,
        "new_zone": new,
        "duration_in_previous": "",
        "duration_seconds": "" if seconds is None else str(int(seconds)),
        "person_entity_id": entity,
    }


HISTORY = [
    # Jean: home since 22:00 the day before, leaves at 08:00 (10 h at home),
    # works until 18:00 (10 h at work), then home again.
    _rec(T0 + timedelta(hours=8), "Jean", "home", "Travail", 10 * 3600, "person.jean"),
    _rec(T0 + timedelta(hours=18), "Jean", "Travail", "home", 10 * 3600, "person.jean"),
    # Marie: away the whole day, no transition (she came back the day after).
    _rec(T0 + timedelta(hours=30), "Marie", "not_home", "home", 40 * 3600, "person.marie"),
]
NOW = T0 + timedelta(hours=36)
STATES = [
    CurrentState("Jean", "home", T0 + timedelta(hours=18), "person.jean"),
    CurrentState("Marie", "home", T0 + timedelta(hours=30), "person.marie"),
]


def test_zone_summary_clips_stays_to_the_period() -> None:
    day_start = T0
    day_end = T0 + timedelta(days=1) - timedelta(microseconds=1)
    summary = zone_summary(HISTORY, STATES, start=day_start, end=day_end, persons=None, now=NOW)

    jean = summary["Jean"]
    # 00:00 -> 08:00 at home (8 h, clipped) + 18:00 -> 24:00 at home (6 h).
    assert jean["home"].seconds == pytest.approx(14 * 3600, abs=1)  # end is 23:59:59.999999
    assert jean["home"].visits == 2  # stay running at midnight + stay from 18:00
    assert jean["home"].ongoing is True
    assert jean["Travail"].seconds == 10 * 3600
    assert jean["Travail"].visits == 1
    assert jean["Travail"].first == T0 + timedelta(hours=8)

    marie = summary["Marie"]
    assert marie["not_home"].seconds == pytest.approx(24 * 3600, abs=1)  # clipped to the day
    assert marie["not_home"].visits == 1  # one stay, running at midnight
    assert "home" not in marie  # her arrival is outside the period


def test_zone_summary_without_bounds_counts_ongoing_stay_until_now() -> None:
    summary = zone_summary(HISTORY, STATES, start=None, end=None, persons=None, now=NOW)
    jean = summary["Jean"]
    # 10 h before 08:00 + 18:00 -> now (18 h) = 28 h
    assert jean["home"].seconds == 28 * 3600
    assert jean["home"].visits == 2  # two distinct stays at home


def test_zone_summary_person_filter_accepts_names_and_entity_ids() -> None:
    by_name = zone_summary(HISTORY, STATES, start=None, end=None, persons={"Marie"}, now=NOW)
    by_entity = zone_summary(
        HISTORY, STATES, start=None, end=None, persons={"person.marie"}, now=NOW
    )
    assert set(by_name) == {"Marie"}
    assert set(by_entity) == {"Marie"}
    assert by_name["Marie"]["home"].seconds == by_entity["Marie"]["home"].seconds == 6 * 3600


def test_summary_as_dict_is_json_friendly() -> None:
    summary = zone_summary(HISTORY, STATES, start=None, end=None, persons=None, now=NOW)
    data = summary_as_dict(summary)
    assert data["Jean"]["Travail"]["seconds"] == 36000
    assert data["Jean"]["Travail"]["first"] == (T0 + timedelta(hours=8)).isoformat()
    assert isinstance(data["Jean"]["home"]["ongoing"], bool)


def test_history_date_range() -> None:
    assert history_date_range([]) is None
    oldest, newest = history_date_range(HISTORY)
    assert oldest == T0 + timedelta(hours=8)
    assert newest == T0 + timedelta(hours=30)


def test_records_without_duration_count_as_visits_only() -> None:
    history = [_rec(T0 + timedelta(hours=1), "Jean", "home", "Travail", None)]
    summary = zone_summary(history, [], start=None, end=None, persons=None, now=NOW)
    assert summary["Jean"]["Travail"].visits == 1
    assert summary["Jean"]["Travail"].seconds == 0
    assert "home" not in summary["Jean"]
