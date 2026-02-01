"""Sensor platform for Suivi de Présence integration."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_HOME, STATE_NOT_HOME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, VERSION

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Suivi Présence sensors based on a config entry."""
    tracker = hass.data[DOMAIN][entry.entry_id]

    entities = [
        PresenceTrackerSensor(hass, entry, tracker),
        PersonsHomeSensor(hass, entry, tracker),
        PersonsAwaySensor(hass, entry, tracker),
        TotalChangesSensor(hass, entry, tracker),
    ]

    async_add_entities(entities, True)


class PresenceTrackerBaseSensor(SensorEntity):
    """Base class for Suivi Présence sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        tracker,
    ) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self.entry = entry
        self.tracker = tracker
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Suivi de Présence",
            manufacturer="Community",
            model="Presence Tracker",
            sw_version=VERSION,
        )

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return True


class PresenceTrackerSensor(PresenceTrackerBaseSensor):
    """Main sensor showing presence tracking status."""

    _attr_icon = "mdi:account-group"
    _attr_name = "Suivi Présence"

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        tracker,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(hass, entry, tracker)
        self._attr_unique_id = f"{entry.entry_id}_main"

    @property
    def native_value(self) -> int:
        """Return the number of tracked persons."""
        return len(self.tracker.person_states)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        persons_home = []
        persons_away = []
        persons_other = []

        for entity_id, data in self.tracker.person_states.items():
            name = data.get("friendly_name", entity_id)
            zone = data.get("zone", "unknown")

            if zone == STATE_HOME:
                persons_home.append(name)
            elif zone == STATE_NOT_HOME:
                persons_away.append(name)
            else:
                persons_other.append(f"{name} ({zone})")

        # Get last change
        last_change = None
        if self.tracker.history:
            last_record = self.tracker.history[-1]
            last_change = last_record.get("timestamp", "")

        return {
            "persons_home": persons_home,
            "persons_away": persons_away,
            "persons_in_zones": persons_other,
            "total_changes_recorded": len(self.tracker.history),
            "last_change": last_change,
            "csv_download_url": "/api/suivi_presence/download",
        }

    async def async_update(self) -> None:
        """Update the sensor."""
        pass  # State is updated via events


class PersonsHomeSensor(PresenceTrackerBaseSensor):
    """Sensor showing number of persons at home."""

    _attr_icon = "mdi:home-account"
    _attr_name = "Personnes à domicile"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        tracker,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(hass, entry, tracker)
        self._attr_unique_id = f"{entry.entry_id}_persons_home"

    @property
    def native_value(self) -> int:
        """Return the number of persons at home."""
        return sum(
            1
            for p in self.tracker.person_states.values()
            if p.get("zone") == STATE_HOME
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        persons = [
            data.get("friendly_name", entity_id)
            for entity_id, data in self.tracker.person_states.items()
            if data.get("zone") == STATE_HOME
        ]
        return {"persons": persons}


class PersonsAwaySensor(PresenceTrackerBaseSensor):
    """Sensor showing number of persons away."""

    _attr_icon = "mdi:home-export-outline"
    _attr_name = "Personnes absentes"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        tracker,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(hass, entry, tracker)
        self._attr_unique_id = f"{entry.entry_id}_persons_away"

    @property
    def native_value(self) -> int:
        """Return the number of persons away."""
        return sum(
            1
            for p in self.tracker.person_states.values()
            if p.get("zone") == STATE_NOT_HOME
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        persons = [
            data.get("friendly_name", entity_id)
            for entity_id, data in self.tracker.person_states.items()
            if data.get("zone") == STATE_NOT_HOME
        ]
        return {"persons": persons}


class TotalChangesSensor(PresenceTrackerBaseSensor):
    """Sensor showing total number of zone changes."""

    _attr_icon = "mdi:counter"
    _attr_name = "Total des changements"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        tracker,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(hass, entry, tracker)
        self._attr_unique_id = f"{entry.entry_id}_total_changes"

    @property
    def native_value(self) -> int:
        """Return the total number of changes."""
        return len(self.tracker.history)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if not self.tracker.history:
            return {"last_change": None}

        last_record = self.tracker.history[-1]
        return {
            "last_change": last_record.get("timestamp", ""),
            "last_person": last_record.get("person", ""),
            "last_from_zone": last_record.get("previous_zone", ""),
            "last_to_zone": last_record.get("new_zone", ""),
        }
