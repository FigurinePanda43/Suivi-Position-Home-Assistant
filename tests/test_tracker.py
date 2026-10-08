"""Behaviour of the tracker inside a running Home Assistant."""

from __future__ import annotations

import csv
from datetime import timedelta
import os

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.suivi_presence.const import CONF_TRACKED_PERSONS, CSV_HEADERS, DOMAIN

TOTAL = "sensor.suivi_de_presence_total_des_changements"
HOME = "sensor.suivi_de_presence_personnes_a_domicile"
AWAY = "sensor.suivi_de_presence_personnes_absentes"


def _rows(csv_path: str) -> list[dict]:
    with open(csv_path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


async def test_zone_change_is_recorded_and_pushed(
    hass: HomeAssistant, setup_integration: MockConfigEntry, csv_path: str
) -> None:
    """A zone change writes a CSV row and updates the sensors immediately (no polling)."""
    tracker = setup_integration.runtime_data
    assert hass.states.get(TOTAL).state == "0"

    hass.states.async_set("person.jean", "Travail", {"friendly_name": "Jean"})
    await hass.async_block_till_done()

    assert hass.states.get(TOTAL).state == "1"
    assert hass.states.get(HOME).state == "0"
    assert hass.states.get(AWAY).state == "1"  # Marie
    total_attrs = hass.states.get(TOTAL).attributes
    assert total_attrs["last_person"] == "Jean"
    assert total_attrs["last_from_zone"] == "home"
    assert total_attrs["last_to_zone"] == "Travail"

    rows = _rows(csv_path)
    assert list(rows[0].keys()) == CSV_HEADERS
    assert len(rows) == 1
    row = rows[0]
    assert row["person"] == "Jean"
    assert row["person_entity_id"] == "person.jean"
    assert row["previous_zone"] == "home"
    assert row["new_zone"] == "Travail"
    # Local time with offset, no microseconds (Europe/Paris -> +01:00 or +02:00).
    assert row["timestamp"].endswith(("+01:00", "+02:00"))
    assert "." not in row["timestamp"]
    # Duration is an integer number of seconds and H:MM:SS.
    assert row["duration_seconds"].isdigit()
    assert row["duration_in_previous"].count(":") == 2
    assert tracker.history[0] == row

    # Attribute-only updates (GPS refresh) must not create records.
    hass.states.async_set("person.jean", "Travail", {"friendly_name": "Jean", "latitude": 1.0})
    await hass.async_block_till_done()
    assert hass.states.get(TOTAL).state == "1"

    main = hass.states.get("sensor.suivi_de_presence_suivi_presence")
    assert main.state == "2"
    assert main.attributes["persons_in_zones"] == {"Jean": "Travail"}
    assert main.attributes["persons_away"] == ["Marie"]
    assert main.attributes["tracking"] is True


async def test_unavailable_then_other_zone_records_one_transition(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """unavailable / unknown are ignored; the real transition is recorded once."""
    hass.states.async_set("person.jean", "unavailable", {"friendly_name": "Jean"})
    await hass.async_block_till_done()
    assert hass.states.get(TOTAL).state == "0"
    tracker = setup_integration.runtime_data
    jean = next(s for s in tracker.current_states if s.entity_id == "person.jean")
    assert jean.extra["available"] is False
    assert jean.zone == "home"  # last known zone kept

    hass.states.async_set("person.jean", "unknown", {"friendly_name": "Jean"})
    await hass.async_block_till_done()
    assert hass.states.get(TOTAL).state == "0"

    hass.states.async_set("person.jean", "not_home", {"friendly_name": "Jean"})
    await hass.async_block_till_done()
    assert hass.states.get(TOTAL).state == "1"
    assert tracker.history[-1]["previous_zone"] == "home"
    assert tracker.history[-1]["new_zone"] == "not_home"

    # Back in the same zone after an outage: nothing recorded.
    hass.states.async_set("person.jean", "unavailable", {"friendly_name": "Jean"})
    await hass.async_block_till_done()
    hass.states.async_set("person.jean", "not_home", {"friendly_name": "Jean"})
    await hass.async_block_till_done()
    assert hass.states.get(TOTAL).state == "1"


async def test_person_created_after_startup_is_tracked(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    hass.states.async_set("person.paul", "home", {"friendly_name": "Paul"})
    await hass.async_block_till_done()
    assert hass.states.get("sensor.suivi_de_presence_suivi_presence").state == "3"
    hass.states.async_set("person.paul", "not_home", {"friendly_name": "Paul"})
    await hass.async_block_till_done()
    assert hass.states.get(TOTAL).state == "1"
    assert setup_integration.runtime_data.history[-1]["person"] == "Paul"

    # Removing the person drops it from the overview.
    hass.states.async_remove("person.paul")
    await hass.async_block_till_done()
    assert hass.states.get("sensor.suivi_de_presence_suivi_presence").state == "2"


async def test_tracked_persons_option_restricts_tracking(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    hass.states.async_set("person.jean", "home", {"friendly_name": "Jean"})
    hass.states.async_set("person.marie", "home", {"friendly_name": "Marie"})
    hass.config_entries.async_update_entry(
        config_entry, options={CONF_TRACKED_PERSONS: ["person.marie"]}
    )
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get("sensor.suivi_de_presence_suivi_presence").state == "1"
    hass.states.async_set("person.jean", "not_home", {"friendly_name": "Jean"})
    await hass.async_block_till_done()
    assert hass.states.get(TOTAL).state == "0"
    hass.states.async_set("person.marie", "not_home", {"friendly_name": "Marie"})
    await hass.async_block_till_done()
    assert hass.states.get(TOTAL).state == "1"


async def test_options_change_reloads_entry(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    old_tracker = setup_integration.runtime_data
    hass.config_entries.async_update_entry(
        setup_integration, options={CONF_TRACKED_PERSONS: ["person.jean"]}
    )
    await hass.async_block_till_done()
    new_tracker = setup_integration.runtime_data
    assert new_tracker is not old_tracker
    assert new_tracker.started
    assert not old_tracker.started
    assert hass.states.get("sensor.suivi_de_presence_suivi_presence").state == "1"


async def test_unload_entry(hass: HomeAssistant, setup_integration: MockConfigEntry) -> None:
    tracker = setup_integration.runtime_data
    assert await hass.config_entries.async_unload(setup_integration.entry_id)
    await hass.async_block_till_done()
    assert not tracker.started
    state = hass.states.get(TOTAL)
    assert state is None or state.state == "unavailable"
    assert hass.data[DOMAIN]["trackers"] == {}
    # A zone change after unload is ignored silently.
    hass.states.async_set("person.jean", "not_home", {"friendly_name": "Jean"})
    await hass.async_block_till_done()
    assert tracker.history == []


async def test_startup_waits_for_home_assistant_started(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """When set up during boot, tracking starts on EVENT_HOMEASSISTANT_STARTED."""
    hass.set_state(hass.state.__class__.starting)
    hass.states.async_set("person.jean", "home", {"friendly_name": "Jean"})
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    tracker = config_entry.runtime_data
    assert not tracker.started
    assert hass.states.get(TOTAL).state == "unavailable"

    hass.set_state(hass.state.__class__.running)
    hass.bus.async_fire("homeassistant_started")
    await hass.async_block_till_done()
    assert tracker.started
    assert hass.states.get(TOTAL).state == "0"
    assert hass.states.get("sensor.suivi_de_presence_suivi_presence").state == "1"


async def test_clear_history_keeps_a_backup(
    hass: HomeAssistant, setup_integration: MockConfigEntry, csv_path: str
) -> None:
    tracker = setup_integration.runtime_data
    hass.states.async_set("person.jean", "not_home", {"friendly_name": "Jean"})
    await hass.async_block_till_done()
    assert len(_rows(csv_path)) == 1

    backup = await tracker.async_clear_history()
    assert os.path.exists(backup)
    assert backup.startswith(csv_path + ".bak-avant-effacement-")
    assert len(_rows(backup)) == 1
    assert _rows(csv_path) == []
    assert tracker.history == []
    assert hass.states.get(TOTAL).state == "0"


async def test_duration_uses_time_since_previous_change(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    tracker = setup_integration.runtime_data
    jean = next(s for s in tracker.current_states if s.entity_id == "person.jean")
    since = jean.since
    later = dt_util.utcnow() + timedelta(hours=2)
    async_fire_time_changed(hass, later)
    # The state machine stamps last_changed with the (frozen) current time: emulate
    # a change happening two hours later by comparing against ``since``.
    hass.states.async_set("person.jean", "not_home", {"friendly_name": "Jean"})
    await hass.async_block_till_done()
    record = tracker.history[-1]
    recorded = int(record["duration_seconds"])
    expected = (dt_util.parse_datetime(record["timestamp"]) - since).total_seconds()
    assert abs(recorded - expected) <= 1
