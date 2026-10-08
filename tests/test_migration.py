"""Loading legacy CSV files and reconciling with the current states at startup."""

from __future__ import annotations

import csv
from datetime import UTC, datetime, timedelta
import glob
import os

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.suivi_presence.const import CSV_HEADERS

LEGACY_HEADER = [
    "timestamp",
    "person",
    "previous_zone",
    "new_zone",
    "duration_in_previous",
    "duration_seconds",
]


def _write_legacy(csv_path: str, rows: list[list[str]], header: list[str] = LEGACY_HEADER) -> None:
    with open(csv_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


async def test_legacy_csv_is_migrated_with_backup(
    hass: HomeAssistant, config_entry: MockConfigEntry, csv_path: str
) -> None:
    yesterday = (dt_util.utcnow() - timedelta(days=1)).replace(microsecond=0)
    _write_legacy(
        csv_path,
        [
            [yesterday.isoformat(), "Jean", "home", "Travail", "12:30:00.500000", "45000.5"],
            [
                (yesterday + timedelta(hours=9)).isoformat(),
                "Jean",
                "Travail",
                "home",
                "9:00:00",
                "32400.0",
            ],
        ],
    )
    hass.states.async_set("person.jean", "home", {"friendly_name": "Jean"})
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    tracker = config_entry.runtime_data
    assert len(tracker.history) == 2
    assert tracker.migrated_from == ",".join(LEGACY_HEADER)
    # Values of the old rows are preserved as-is; the new column is empty.
    assert tracker.history[0]["duration_seconds"] == "45000.5"
    assert tracker.history[0]["person_entity_id"] == ""

    with open(csv_path, encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    assert rows[0] == CSV_HEADERS
    assert len(rows) == 3
    backups = glob.glob(csv_path + ".bak-migration-*")
    assert len(backups) == 1
    with open(backups[0], encoding="utf-8", newline="") as handle:
        assert next(csv.reader(handle)) == LEGACY_HEADER

    # The sensors see the loaded history.
    assert hass.states.get("sensor.suivi_de_presence_total_des_changements").state == "2"

    # Jean is still "home" like the last record: the stay started at that record.
    jean = next(s for s in tracker.current_states if s.entity_id == "person.jean")
    assert jean.since == yesterday + timedelta(hours=9)


async def test_very_old_csv_without_duration_seconds(
    hass: HomeAssistant, config_entry: MockConfigEntry, csv_path: str
) -> None:
    _write_legacy(
        csv_path,
        [["2025-01-01T08:00:00+00:00", "Jean", "home", "not_home", "1 day, 2:00:00"]],
        header=LEGACY_HEADER[:5],
    )
    hass.states.async_set("person.jean", "not_home", {"friendly_name": "Jean"})
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    tracker = config_entry.runtime_data
    assert len(tracker.history) == 1
    assert tracker.history[0]["duration_seconds"] == ""
    assert tracker.history[0]["duration_in_previous"] == "1 day, 2:00:00"
    with open(csv_path, encoding="utf-8", newline="") as handle:
        assert next(csv.reader(handle)) == CSV_HEADERS


async def test_missed_transition_while_stopped_is_recorded(
    hass: HomeAssistant, config_entry: MockConfigEntry, csv_path: str
) -> None:
    """Last record says Jean arrived at work, but Jean is home now: record work -> home."""
    two_hours_ago = (dt_util.utcnow() - timedelta(hours=2)).replace(microsecond=0)
    _write_legacy(
        csv_path,
        [[two_hours_ago.isoformat(), "Jean", "home", "Travail", "1:00:00", "3600"]],
    )
    hass.states.async_set("person.jean", "home", {"friendly_name": "Jean"})
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    tracker = config_entry.runtime_data
    assert len(tracker.history) == 2
    missed = tracker.history[-1]
    assert missed["person"] == "Jean"
    assert missed["person_entity_id"] == "person.jean"
    assert missed["previous_zone"] == "Travail"
    assert missed["new_zone"] == "home"
    # Duration = time between the last record and the detected change (~2 h).
    assert abs(int(missed["duration_seconds"]) - 7200) < 120
    assert hass.states.get("sensor.suivi_de_presence_total_des_changements").state == "2"


async def test_unknown_person_state_at_startup_is_ignored(
    hass: HomeAssistant, config_entry: MockConfigEntry, csv_path: str
) -> None:
    _write_legacy(
        csv_path, [["2025-01-01T08:00:00+00:00", "Jean", "home", "Travail", "1:00:00", "3600"]]
    )
    hass.states.async_set("person.jean", "unknown", {"friendly_name": "Jean"})
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    tracker = config_entry.runtime_data
    assert tracker.current_states == []
    assert len(tracker.history) == 1
    # First real state afterwards is simply adopted (no record: nothing to compare against
    # in memory, the CSV comparison only happens at startup).
    hass.states.async_set("person.jean", "home", {"friendly_name": "Jean"})
    await hass.async_block_till_done()
    assert len(tracker.current_states) == 1
    assert len(tracker.history) == 1


async def test_unexpected_header_is_loaded_but_flagged(
    hass: HomeAssistant, config_entry: MockConfigEntry, csv_path: str
) -> None:
    _write_legacy(
        csv_path,
        [["2025-01-01T08:00:00+00:00", "Jean", "home", "Travail", "x"]],
        header=["timestamp", "person", "previous_zone", "new_zone", "custom_column"],
    )
    hass.states.async_set("person.jean", "Travail", {"friendly_name": "Jean"})
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    tracker = config_entry.runtime_data
    assert tracker.load_error is not None
    assert len(tracker.history) == 1
    assert tracker.history[0]["new_zone"] == "Travail"
    assert not os.path.exists(csv_path + ".bak-migration")
    assert datetime(2025, 1, 1, tzinfo=UTC)  # keep import used
