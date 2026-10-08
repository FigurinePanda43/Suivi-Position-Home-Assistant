"""Sensor platform: a handful of lightweight, push-updated counters.

Entity names are fixed (French) on purpose: the entity ids derived from them
(``sensor.suivi_de_presence_*``) are documented and used by the example dashboard,
and must not depend on the Home Assistant UI language.

Detailed data (history, per-zone statistics) is deliberately *not* exposed as
entity attributes: it would be written into the recorder database on every
change. The card fetches it through the websocket API instead.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_HOME, STATE_NOT_HOME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .export import get_date_range_info
from .tracker import PresenceTracker


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensors of a config entry."""
    tracker: PresenceTracker = entry.runtime_data
    version = hass.data.get(DOMAIN, {}).get("version")
    async_add_entities(
        [
            PresenceTrackerSensor(entry, tracker, version),
            PersonsHomeSensor(entry, tracker, version),
            PersonsAwaySensor(entry, tracker, version),
            TotalChangesSensor(entry, tracker, version),
        ]
    )


class PresenceBaseSensor(SensorEntity):
    """Common behaviour: push updates from the tracker, shared device."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self, entry: ConfigEntry, tracker: PresenceTracker, version: str | None, suffix: str
    ) -> None:
        self.tracker = tracker
        self._attr_unique_id = f"{entry.entry_id}_{suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Suivi de Présence",
            manufacturer="Community",
            model="Presence Tracker",
            sw_version=version,
            entry_type=DeviceEntryType.SERVICE,
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to tracker updates."""
        self.async_on_remove(self.tracker.async_add_listener(self._handle_update))

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """The sensors are meaningful only once the tracker runs."""
        return self.tracker.started

    def _names_in(self, zone: str) -> list[str]:
        return sorted(s.person for s in self.tracker.current_states if s.zone == zone)


class PresenceTrackerSensor(PresenceBaseSensor):
    """Number of tracked persons, with a compact summary of who is where."""

    _attr_icon = "mdi:account-group"
    _attr_name = "Suivi Présence"
    _unrecorded_attributes = frozenset({"data_range", "csv_path", "tracking"})

    def __init__(self, entry: ConfigEntry, tracker: PresenceTracker, version: str | None) -> None:
        super().__init__(entry, tracker, version, "main")

    @property
    def native_value(self) -> int:
        """Return the number of tracked persons."""
        return len(self.tracker.current_states)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return a small summary (lists of names)."""
        persons_other = {
            s.person: s.zone
            for s in self.tracker.current_states
            if s.zone not in (STATE_HOME, STATE_NOT_HOME)
        }
        history = self.tracker.history
        last = history[-1] if history else None
        return {
            "persons_home": self._names_in(STATE_HOME),
            "persons_away": self._names_in(STATE_NOT_HOME),
            "persons_in_zones": persons_other,
            "total_changes_recorded": len(history),
            "last_change": last.get("timestamp") if last else None,
            "data_range": get_date_range_info(history),
            "csv_path": self.tracker.csv_path,
            "tracking": self.tracker.started,
        }


class PersonsHomeSensor(PresenceBaseSensor):
    """Number of persons at home."""

    _attr_icon = "mdi:home-account"
    _attr_name = "Personnes à domicile"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, entry: ConfigEntry, tracker: PresenceTracker, version: str | None) -> None:
        super().__init__(entry, tracker, version, "persons_home")

    @property
    def native_value(self) -> int:
        """Return the number of persons at home."""
        return len(self._names_in(STATE_HOME))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the names."""
        return {"persons": self._names_in(STATE_HOME)}


class PersonsAwaySensor(PresenceBaseSensor):
    """Number of persons away (outside every known zone)."""

    _attr_icon = "mdi:home-export-outline"
    _attr_name = "Personnes absentes"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, entry: ConfigEntry, tracker: PresenceTracker, version: str | None) -> None:
        super().__init__(entry, tracker, version, "persons_away")

    @property
    def native_value(self) -> int:
        """Return the number of persons away."""
        return len(self._names_in(STATE_NOT_HOME))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the names."""
        return {"persons": self._names_in(STATE_NOT_HOME)}


class TotalChangesSensor(PresenceBaseSensor):
    """Total number of recorded zone changes."""

    _attr_icon = "mdi:counter"
    _attr_name = "Total des changements"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, entry: ConfigEntry, tracker: PresenceTracker, version: str | None) -> None:
        super().__init__(entry, tracker, version, "total_changes")

    @property
    def native_value(self) -> int:
        """Return the number of records."""
        return len(self.tracker.history)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Describe the last change."""
        history = self.tracker.history
        if not history:
            return {"last_change": None}
        last = history[-1]
        return {
            "last_change": last.get("timestamp"),
            "last_person": last.get("person"),
            "last_from_zone": last.get("previous_zone"),
            "last_to_zone": last.get("new_zone"),
        }
