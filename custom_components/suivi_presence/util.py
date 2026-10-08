"""Date, time and duration helpers shared by the whole integration.

All timestamps handled internally are timezone-aware ``datetime`` objects.
Strings stored in the CSV are ISO 8601 with an explicit UTC offset; versions
<= 0.1.1 stored UTC (``+00:00``), version 1.0.0 stores local time with its
offset, which is more readable in the raw file. Both parse back identically.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
import re

from homeassistant.util import dt as dt_util

_LEGACY_TIMEDELTA_RE = re.compile(
    r"^(?:(?P<days>-?\d+) days?, )?(?P<hours>\d+):(?P<minutes>\d{2}):(?P<seconds>\d{2}(?:\.\d+)?)$"
)
_HMS_RE = re.compile(r"^(?P<hours>\d+):(?P<minutes>\d{2}):(?P<seconds>\d{2})$")


def parse_timestamp(value: str | None) -> datetime | None:
    """Parse a stored ISO 8601 timestamp into an aware UTC datetime.

    Naive values (should not happen with files written by this integration) are
    interpreted in the Home Assistant time zone.
    """
    if not value:
        return None
    parsed = dt_util.parse_datetime(value)
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt_util.get_default_time_zone())
    return dt_util.as_utc(parsed)


def format_timestamp(value: datetime) -> str:
    """Format a datetime for CSV storage: local time, second precision, with offset."""
    return dt_util.as_local(value).replace(microsecond=0).isoformat()


def parse_user_datetime(value: str | None, *, end_of_day: bool = False) -> datetime | None:
    """Parse a user supplied date or datetime (filters) into an aware UTC datetime.

    Accepted: ``YYYY-MM-DD`` (interpreted as the start, or the end, of that local
    day) and any ISO 8601 datetime. A datetime without offset is local time.
    Returns ``None`` for empty or invalid input.
    """
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None

    tz = dt_util.get_default_time_zone()
    as_date = dt_util.parse_date(value) if len(value) == 10 else None
    if as_date is not None:
        bound = time.max if end_of_day else time.min
        return dt_util.as_utc(datetime.combine(as_date, bound, tzinfo=tz))

    parsed = dt_util.parse_datetime(value)
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=tz)
    return dt_util.as_utc(parsed)


def parse_duration_seconds(record: dict) -> float | None:
    """Return the duration (seconds) spent in the previous zone for a CSV record.

    Reads ``duration_seconds`` first, then falls back to ``duration_in_previous``
    which may be either the 1.0.0 ``H:MM:SS`` format or the legacy
    ``str(timedelta)`` format (``1 day, 2:03:04.567890``).
    """
    raw = record.get("duration_seconds")
    if raw not in (None, ""):
        try:
            seconds = float(raw)
        except (TypeError, ValueError):
            seconds = None
        else:
            return seconds if seconds >= 0 else None

    text = (record.get("duration_in_previous") or "").strip()
    if not text:
        return None
    match = _HMS_RE.match(text) or _LEGACY_TIMEDELTA_RE.match(text)
    if match is None:
        return None
    days = int(match.groupdict().get("days") or 0)
    hours = int(match.group("hours"))
    minutes = int(match.group("minutes"))
    seconds = float(match.group("seconds"))
    total = timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds).total_seconds()
    return total if total >= 0 else None


def format_duration_hms(seconds: float | None) -> str:
    """Format seconds as ``H:MM:SS`` (hours may exceed 24). Empty string if unknown."""
    if seconds is None or seconds < 0:
        return ""
    total = int(round(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}"


def format_duration_human(seconds: float | None, language: str = "fr") -> str:
    """Format seconds as a short human readable string (``1 j 2 h 05 min``)."""
    if seconds is None or seconds < 0:
        return "—"
    total = int(round(seconds))
    days, remainder = divmod(total, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)
    day_unit = "j" if language.startswith("fr") else "d"
    if days > 0:
        return f"{days} {day_unit} {hours} h {minutes:02d} min"
    if hours > 0:
        return f"{hours} h {minutes:02d} min"
    if minutes > 0:
        return f"{minutes} min {secs:02d} s"
    return f"{secs} s"


def local_naive(value: datetime) -> datetime:
    """Return the local wall-clock time of an aware datetime, without tzinfo (for Excel)."""
    return dt_util.as_local(value).replace(tzinfo=None, microsecond=0)


def period_days(
    start: datetime | None, end: datetime | None, fallback: tuple[datetime, datetime] | None
) -> float:
    """Return the length of a period in days (minimum 1), used for averages."""
    if start is None or end is None:
        if fallback is None:
            return 1.0
        f_start, f_end = fallback
        start = start or f_start
        end = end or f_end
    delta = (end - start).total_seconds() / 86400
    return max(delta, 1.0)


def start_of_local_day(value: datetime) -> datetime:
    """Return the UTC datetime of midnight (local time) of the day containing ``value``."""
    local = dt_util.as_local(value)
    return dt_util.as_utc(datetime.combine(local.date(), time.min, tzinfo=local.tzinfo))


def local_date(value: datetime) -> date:
    """Return the local calendar date of an aware datetime."""
    return dt_util.as_local(value).date()
