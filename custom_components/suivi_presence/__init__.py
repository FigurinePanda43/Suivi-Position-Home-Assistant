"""
Suivi de Présence - Integration for Home Assistant.

This integration tracks person movements between zones and records them to CSV.
"""
from __future__ import annotations

import asyncio
import csv
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EVENT_HOMEASSISTANT_STARTED,
    EVENT_STATE_CHANGED,
    STATE_HOME,
    STATE_NOT_HOME,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_DURATION,
    ATTR_NEW_ZONE,
    ATTR_PERSON,
    ATTR_PREVIOUS_ZONE,
    ATTR_TIMESTAMP,
    CONF_CSV_PATH,
    CONF_SCAN_INTERVAL,
    CSV_HEADERS,
    DEFAULT_CSV_FILENAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    HTTP_DATA_PATH,
    HTTP_DOWNLOAD_PATH,
    PLATFORMS,
    SERVICE_CLEAR_HISTORY,
    SERVICE_EXPORT_CSV,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Suivi Présence component from YAML."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Suivi Présence from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Get configuration
    csv_path = entry.data.get(CONF_CSV_PATH) or os.path.join(
        hass.config.path(), DEFAULT_CSV_FILENAME
    )

    # Initialize the presence tracker
    tracker = PresenceTracker(hass, csv_path, entry)
    hass.data[DOMAIN][entry.entry_id] = tracker

    # Start tracking after Home Assistant is fully started
    async def start_tracking(_event: Event) -> None:
        await tracker.async_start()

    if hass.is_running:
        await tracker.async_start()
    else:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, start_tracking)

    # Register services
    await async_register_services(hass, tracker)

    # Register HTTP views for download
    await async_register_http_views(hass, tracker)

    # Forward entry setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        tracker = hass.data[DOMAIN].pop(entry.entry_id)
        await tracker.async_stop()

    return unload_ok


async def async_register_services(
    hass: HomeAssistant, tracker: "PresenceTracker"
) -> None:
    """Register integration services."""

    async def handle_export_csv(call) -> None:
        """Handle the export_csv service call."""
        filename = call.data.get("filename")
        await tracker.async_export_csv(filename)

    async def handle_clear_history(call) -> None:
        """Handle the clear_history service call."""
        await tracker.async_clear_history()

    hass.services.async_register(DOMAIN, SERVICE_EXPORT_CSV, handle_export_csv)
    hass.services.async_register(DOMAIN, SERVICE_CLEAR_HISTORY, handle_clear_history)


async def async_register_http_views(
    hass: HomeAssistant, tracker: "PresenceTracker"
) -> None:
    """Register HTTP views for CSV download."""
    from aiohttp import web

    async def download_csv(request: web.Request) -> web.Response:
        """Handle CSV download request."""
        csv_content = await tracker.async_get_csv_content()
        return web.Response(
            body=csv_content,
            content_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{DEFAULT_CSV_FILENAME}"'
            },
        )

    async def get_data(request: web.Request) -> web.Response:
        """Handle data request for dashboard."""
        import json

        data = await tracker.async_get_dashboard_data()
        return web.Response(
            body=json.dumps(data),
            content_type="application/json",
        )

    hass.http.register_view(DownloadCSVView(tracker))
    hass.http.register_view(DashboardDataView(tracker))


class DownloadCSVView:
    """View to handle CSV downloads."""

    url = HTTP_DOWNLOAD_PATH
    name = "api:suivi_presence:download"
    requires_auth = True

    def __init__(self, tracker: "PresenceTracker") -> None:
        """Initialize the view."""
        self.tracker = tracker

    async def get(self, request) -> Any:
        """Handle GET request."""
        from aiohttp import web

        csv_content = await self.tracker.async_get_csv_content()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"suivi_presence_{timestamp}.csv"

        return web.Response(
            body=csv_content,
            content_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )


class DashboardDataView:
    """View to handle dashboard data requests."""

    url = HTTP_DATA_PATH
    name = "api:suivi_presence:data"
    requires_auth = True

    def __init__(self, tracker: "PresenceTracker") -> None:
        """Initialize the view."""
        self.tracker = tracker

    async def get(self, request) -> Any:
        """Handle GET request."""
        from aiohttp import web
        import json

        data = await self.tracker.async_get_dashboard_data()
        return web.Response(
            body=json.dumps(data, ensure_ascii=False, default=str),
            content_type="application/json; charset=utf-8",
        )


class PresenceTracker:
    """Class to track presence changes and record to CSV."""

    def __init__(
        self, hass: HomeAssistant, csv_path: str, entry: ConfigEntry
    ) -> None:
        """Initialize the presence tracker."""
        self.hass = hass
        self.csv_path = csv_path
        self.entry = entry
        self._unsub_state_changed: list = []
        self._person_states: dict[str, dict] = {}
        self._history: list[dict] = []
        self._lock = asyncio.Lock()

    async def async_start(self) -> None:
        """Start tracking presence changes."""
        _LOGGER.info("Starting Suivi Présence tracker")

        # Load existing CSV data
        await self._async_load_csv()

        # Get all person entities
        persons = await self._async_get_persons()

        # Initialize states for all persons
        for person_id in persons:
            state = self.hass.states.get(person_id)
            if state:
                self._person_states[person_id] = {
                    "zone": state.state,
                    "last_changed": state.last_changed,
                    "friendly_name": state.attributes.get("friendly_name", person_id),
                }

        # Track state changes for person entities
        @callback
        def async_state_changed(event: Event) -> None:
            """Handle person state changes."""
            self.hass.async_create_task(self._async_handle_state_change(event))

        self._unsub_state_changed.append(
            async_track_state_change_event(
                self.hass, list(persons), async_state_changed
            )
        )

        _LOGGER.info(f"Tracking {len(persons)} persons: {list(persons)}")

    async def async_stop(self) -> None:
        """Stop tracking presence changes."""
        for unsub in self._unsub_state_changed:
            unsub()
        self._unsub_state_changed.clear()
        _LOGGER.info("Stopped Suivi Présence tracker")

    async def _async_get_persons(self) -> set[str]:
        """Get all person entity IDs."""
        persons = set()
        states = self.hass.states.async_all("person")
        for state in states:
            persons.add(state.entity_id)
        return persons

    async def _async_handle_state_change(self, event: Event) -> None:
        """Handle a state change event for a person."""
        entity_id = event.data.get("entity_id")
        old_state: State | None = event.data.get("old_state")
        new_state: State | None = event.data.get("new_state")

        if not entity_id or not new_state:
            return

        # Skip unavailable/unknown states
        if new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return

        old_zone = old_state.state if old_state else STATE_UNKNOWN
        new_zone = new_state.state

        # Skip if no actual change
        if old_zone == new_zone:
            return

        # Skip initial unavailable to real state transitions
        if old_zone in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            # Just update state without recording
            self._person_states[entity_id] = {
                "zone": new_zone,
                "last_changed": new_state.last_changed,
                "friendly_name": new_state.attributes.get("friendly_name", entity_id),
            }
            return

        # Calculate duration in previous zone
        duration = None
        if entity_id in self._person_states:
            last_changed = self._person_states[entity_id].get("last_changed")
            if last_changed:
                duration = new_state.last_changed - last_changed

        # Record the change
        friendly_name = new_state.attributes.get("friendly_name", entity_id)
        await self._async_record_change(
            person=friendly_name,
            previous_zone=old_zone,
            new_zone=new_zone,
            timestamp=new_state.last_changed,
            duration=duration,
        )

        # Update tracked state
        self._person_states[entity_id] = {
            "zone": new_zone,
            "last_changed": new_state.last_changed,
            "friendly_name": friendly_name,
        }

        _LOGGER.debug(
            f"Person {friendly_name} moved from {old_zone} to {new_zone}"
        )

    async def _async_record_change(
        self,
        person: str,
        previous_zone: str,
        new_zone: str,
        timestamp: datetime,
        duration: timedelta | None,
    ) -> None:
        """Record a zone change to history and CSV."""
        duration_str = str(duration) if duration else ""

        record = {
            ATTR_TIMESTAMP: timestamp.isoformat(),
            ATTR_PERSON: person,
            ATTR_PREVIOUS_ZONE: previous_zone,
            ATTR_NEW_ZONE: new_zone,
            ATTR_DURATION: duration_str,
        }

        async with self._lock:
            self._history.append(record)
            await self._async_write_csv_row(record)

    async def _async_load_csv(self) -> None:
        """Load existing CSV data."""
        if not os.path.exists(self.csv_path):
            # Create new CSV with headers
            await self._async_create_csv()
            return

        try:

            def read_csv():
                records = []
                with open(self.csv_path, "r", encoding="utf-8", newline="") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        records.append(row)
                return records

            self._history = await self.hass.async_add_executor_job(read_csv)
            _LOGGER.info(f"Loaded {len(self._history)} records from CSV")

        except Exception as e:
            _LOGGER.error(f"Error loading CSV: {e}")
            self._history = []

    async def _async_create_csv(self) -> None:
        """Create a new CSV file with headers."""

        def create_csv():
            os.makedirs(os.path.dirname(self.csv_path), exist_ok=True) if os.path.dirname(
                self.csv_path
            ) else None
            with open(self.csv_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(CSV_HEADERS)

        await self.hass.async_add_executor_job(create_csv)
        _LOGGER.info(f"Created new CSV file: {self.csv_path}")

    async def _async_write_csv_row(self, record: dict) -> None:
        """Write a single row to the CSV file."""

        def write_row():
            with open(self.csv_path, "a", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        record[ATTR_TIMESTAMP],
                        record[ATTR_PERSON],
                        record[ATTR_PREVIOUS_ZONE],
                        record[ATTR_NEW_ZONE],
                        record[ATTR_DURATION],
                    ]
                )

        await self.hass.async_add_executor_job(write_row)

    async def async_export_csv(self, filename: str | None = None) -> str:
        """Export history to a CSV file."""
        if filename:
            export_path = os.path.join(self.hass.config.path(), filename)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_path = os.path.join(
                self.hass.config.path(), f"suivi_presence_export_{timestamp}.csv"
            )

        def write_export():
            with open(export_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(CSV_HEADERS)
                for record in self._history:
                    writer.writerow(
                        [
                            record.get(ATTR_TIMESTAMP, ""),
                            record.get(ATTR_PERSON, ""),
                            record.get(ATTR_PREVIOUS_ZONE, ""),
                            record.get(ATTR_NEW_ZONE, ""),
                            record.get(ATTR_DURATION, ""),
                        ]
                    )

        await self.hass.async_add_executor_job(write_export)
        _LOGGER.info(f"Exported {len(self._history)} records to {export_path}")
        return export_path

    async def async_clear_history(self) -> None:
        """Clear all recorded history."""
        async with self._lock:
            self._history.clear()
            await self._async_create_csv()
        _LOGGER.info("Cleared presence history")

    async def async_get_csv_content(self) -> str:
        """Get CSV content as string for download."""
        import io

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(CSV_HEADERS)

        for record in self._history:
            writer.writerow(
                [
                    record.get(ATTR_TIMESTAMP, ""),
                    record.get(ATTR_PERSON, ""),
                    record.get(ATTR_PREVIOUS_ZONE, ""),
                    record.get(ATTR_NEW_ZONE, ""),
                    record.get(ATTR_DURATION, ""),
                ]
            )

        return output.getvalue()

    async def async_get_dashboard_data(self) -> dict:
        """Get data for the dashboard."""
        # Current status of all persons
        current_status = []
        for entity_id, data in self._person_states.items():
            current_status.append(
                {
                    "entity_id": entity_id,
                    "name": data.get("friendly_name", entity_id),
                    "zone": data.get("zone", STATE_UNKNOWN),
                    "last_changed": data.get("last_changed", "").isoformat()
                    if data.get("last_changed")
                    else "",
                }
            )

        # Recent history (last 50 entries)
        recent_history = self._history[-50:] if self._history else []

        # Statistics
        total_changes = len(self._history)
        persons_home = sum(
            1
            for p in self._person_states.values()
            if p.get("zone") == STATE_HOME
        )
        persons_away = sum(
            1
            for p in self._person_states.values()
            if p.get("zone") == STATE_NOT_HOME
        )

        return {
            "current_status": current_status,
            "recent_history": recent_history,
            "statistics": {
                "total_changes": total_changes,
                "persons_home": persons_home,
                "persons_away": persons_away,
                "total_persons": len(self._person_states),
            },
            "csv_download_url": HTTP_DOWNLOAD_PATH,
        }

    @property
    def history(self) -> list[dict]:
        """Return the history."""
        return self._history

    @property
    def person_states(self) -> dict[str, dict]:
        """Return current person states."""
        return self._person_states
