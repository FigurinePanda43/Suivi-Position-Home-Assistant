"""Zone statistics computed from the recorded history.

The CSV stores *transitions*: at ``timestamp`` the person left ``previous_zone``
(where they had stayed ``duration_seconds``) and entered ``new_zone``. From this
we rebuild *stays* (intervals spent in a zone) and clip them to the requested
period, which gives exact "time spent per zone" figures for any period, including
the stay that is still in progress.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from .const import (
    ATTR_NEW_ZONE,
    ATTR_PERSON,
    ATTR_PERSON_ENTITY_ID,
    ATTR_PREVIOUS_ZONE,
    ATTR_TIMESTAMP,
)
from .util import parse_duration_seconds, parse_timestamp


@dataclass(slots=True)
class Stay:
    """An interval spent by a person in a zone. ``end`` is None while ongoing."""

    person: str
    zone: str
    start: datetime
    end: datetime | None


@dataclass(slots=True)
class ZoneStats:
    """Aggregated figures for one person in one zone over a period."""

    seconds: float = 0.0
    visits: int = 0
    first: datetime | None = None
    last: datetime | None = None
    ongoing: bool = False

    def as_dict(self) -> dict[str, Any]:
        """Serialise for JSON / websocket consumers."""
        return {
            "seconds": round(self.seconds),
            "visits": self.visits,
            "first": self.first.isoformat() if self.first else None,
            "last": self.last.isoformat() if self.last else None,
            "ongoing": self.ongoing,
        }


@dataclass(slots=True)
class CurrentState:
    """Current zone of a tracked person (from the tracker)."""

    person: str
    zone: str
    since: datetime | None
    entity_id: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


def record_person_matches(record: dict, selection: set[str] | None) -> bool:
    """Return True if a record belongs to one of the selected persons.

    ``selection`` may contain friendly names or ``person.*`` entity ids.
    """
    if not selection:
        return True
    return (record.get(ATTR_PERSON) or "") in selection or (
        record.get(ATTR_PERSON_ENTITY_ID) or ""
    ) in selection


def state_person_matches(state: CurrentState, selection: set[str] | None) -> bool:
    """Return True if a current state belongs to one of the selected persons."""
    if not selection:
        return True
    return state.person in selection or (state.entity_id or "") in selection


def build_stays(
    history: list[dict],
    current_states: list[CurrentState],
    now: datetime,
) -> list[Stay]:
    """Rebuild stays from transitions and current states."""
    stays: list[Stay] = []
    for record in history:
        end = parse_timestamp(record.get(ATTR_TIMESTAMP))
        if end is None:
            continue
        duration = parse_duration_seconds(record)
        zone = record.get(ATTR_PREVIOUS_ZONE) or ""
        if duration is None or not zone:
            continue
        stays.append(
            Stay(
                person=record.get(ATTR_PERSON) or "",
                zone=zone,
                start=end - timedelta(seconds=duration),
                end=end,
            )
        )
    for state in current_states:
        if state.since is None or not state.zone:
            continue
        stays.append(Stay(person=state.person, zone=state.zone, start=state.since, end=None))

    # Arrivals whose stay could not be rebuilt (last record of a person with no
    # current state, broken legacy chain): keep a zero-length stay so that the
    # visit is still counted.
    known_starts: dict[tuple[str, str], list[datetime]] = defaultdict(list)
    for stay in stays:
        known_starts[(stay.person, stay.zone)].append(stay.start)
    tolerance = timedelta(seconds=2)
    for record in history:
        ts = parse_timestamp(record.get(ATTR_TIMESTAMP))
        person = record.get(ATTR_PERSON) or ""
        zone = record.get(ATTR_NEW_ZONE) or ""
        if ts is None or not person or not zone:
            continue
        if any(abs(start - ts) <= tolerance for start in known_starts.get((person, zone), ())):
            continue
        stays.append(Stay(person=person, zone=zone, start=ts, end=ts))
    return stays


def zone_summary(
    history: list[dict],
    current_states: list[CurrentState],
    *,
    start: datetime | None,
    end: datetime | None,
    persons: set[str] | None,
    now: datetime,
) -> dict[str, dict[str, ZoneStats]]:
    """Return ``{person: {zone: ZoneStats}}`` for the period ``[start, end]``.

    * time spent = sum of the stays clipped to the period (ongoing stays are
      clipped to ``min(end, now)``);
    * visits = number of distinct stays in the zone overlapping the period (a
      stay already running when the period starts counts as one);
    * first / last = first and last recorded arrival inside the period.
    """
    period_start = start
    period_end = min(end, now) if end else now

    selected_history = [r for r in history if record_person_matches(r, persons)]
    selected_states = [s for s in current_states if state_person_matches(s, persons)]

    result: dict[str, dict[str, ZoneStats]] = defaultdict(lambda: defaultdict(ZoneStats))

    # Time spent and visits, from clipped stays.
    for stay in build_stays(selected_history, selected_states, now):
        if not stay.person:
            continue
        s_start = stay.start
        s_end = stay.end or now
        clip_start = max(s_start, period_start) if period_start else s_start
        clip_end = min(s_end, period_end)
        if clip_end < clip_start:
            continue
        if clip_end == clip_start and (stay.end is None or stay.end != stay.start):
            continue  # real stay entirely outside the period
        stats = result[stay.person][stay.zone]
        stats.seconds += (clip_end - clip_start).total_seconds()
        stats.visits += 1
        if stay.end is None:
            stats.ongoing = True

    # First / last recorded arrival inside the period.
    for record in selected_history:
        ts = parse_timestamp(record.get(ATTR_TIMESTAMP))
        if ts is None:
            continue
        if period_start and ts < period_start:
            continue
        if ts > period_end:
            continue
        person = record.get(ATTR_PERSON) or ""
        zone = record.get(ATTR_NEW_ZONE) or ""
        if not person or not zone:
            continue
        stats = result[person][zone]
        if stats.first is None or ts < stats.first:
            stats.first = ts
        if stats.last is None or ts > stats.last:
            stats.last = ts

    # Plain dicts (no defaultdict leaking out).
    return {person: dict(zones) for person, zones in result.items()}


def summary_as_dict(
    summary: dict[str, dict[str, ZoneStats]],
) -> dict[str, dict[str, dict[str, Any]]]:
    """Serialise a zone summary for JSON."""
    return {
        person: {zone: stats.as_dict() for zone, stats in sorted(zones.items())}
        for person, zones in sorted(summary.items())
    }


def history_date_range(history: list[dict]) -> tuple[datetime, datetime] | None:
    """Return (oldest, newest) timestamps found in the history, or None."""
    oldest: datetime | None = None
    newest: datetime | None = None
    for record in history:
        ts = parse_timestamp(record.get(ATTR_TIMESTAMP))
        if ts is None:
            continue
        if oldest is None or ts < oldest:
            oldest = ts
        if newest is None or ts > newest:
            newest = ts
    if oldest is None or newest is None:
        return None
    return oldest, newest
