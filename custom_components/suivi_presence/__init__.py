"""
Suivi de Présence - Integration for Home Assistant.

This integration tracks person movements between zones and records them to CSV.
The CSV file serves as the permanent data source (Home Assistant only keeps 10 days).
"""
from __future__ import annotations

import asyncio
import csv
import logging
import os
from datetime import datetime, timedelta
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EVENT_HOMEASSISTANT_STARTED,
    STATE_HOME,
    STATE_NOT_HOME,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import Event, HomeAssistant, ServiceCall, State, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_DURATION,
    ATTR_DURATION_SECONDS,
    ATTR_END_DATE,
    ATTR_FILENAME,
    ATTR_NEW_ZONE,
    ATTR_PERSON,
    ATTR_PERSONS,
    ATTR_PREVIOUS_ZONE,
    ATTR_START_DATE,
    ATTR_TIMESTAMP,
    CONF_CSV_PATH,
    CSV_HEADERS,
    DEFAULT_CSV_FILENAME,
    DOMAIN,
    HTTP_DATA_PATH,
    HTTP_DOWNLOAD_CSV_FILTERED,
    HTTP_DOWNLOAD_EXCEL,
    HTTP_DOWNLOAD_PATH,
    PLATFORMS,
    SERVICE_CLEAR_HISTORY,
    SERVICE_EXPORT_CSV,
    SERVICE_EXPORT_EXCEL,
)
from .export import (
    export_to_csv,
    export_to_excel,
    filter_history,
    get_date_range_info,
    get_unique_persons,
)

_LOGGER = logging.getLogger(__name__)

# Service schemas
SERVICE_EXPORT_CSV_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_FILENAME): cv.string,
        vol.Optional(ATTR_START_DATE): cv.string,
        vol.Optional(ATTR_END_DATE): cv.string,
        vol.Optional(ATTR_PERSONS): vol.All(cv.ensure_list, [cv.string]),
    }
)

SERVICE_EXPORT_EXCEL_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_FILENAME): cv.string,
        vol.Optional(ATTR_START_DATE): cv.string,
        vol.Optional(ATTR_END_DATE): cv.string,
        vol.Optional(ATTR_PERSONS): vol.All(cv.ensure_list, [cv.string]),
    }
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Suivi Présence component from YAML."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Suivi Présence from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Get configuration - CSV path for permanent storage
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
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        tracker = hass.data[DOMAIN].pop(entry.entry_id)
        await tracker.async_stop()

    return unload_ok


async def async_register_services(
    hass: HomeAssistant, tracker: "PresenceTracker"
) -> None:
    """Register integration services."""

    async def handle_export_csv(call: ServiceCall) -> None:
        """Handle the export_csv service call with date filtering."""
        filename = call.data.get(ATTR_FILENAME)
        start_date_str = call.data.get(ATTR_START_DATE)
        end_date_str = call.data.get(ATTR_END_DATE)
        persons = call.data.get(ATTR_PERSONS)

        # Parse dates
        start_date = None
        end_date = None
        if start_date_str:
            try:
                start_date = datetime.fromisoformat(start_date_str)
            except ValueError:
                _LOGGER.warning(f"Invalid start_date format: {start_date_str}")

        if end_date_str:
            try:
                end_date = datetime.fromisoformat(end_date_str)
            except ValueError:
                _LOGGER.warning(f"Invalid end_date format: {end_date_str}")

        await tracker.async_export_csv_filtered(filename, start_date, end_date, persons)

    async def handle_export_excel(call: ServiceCall) -> None:
        """Handle the export_excel service call."""
        filename = call.data.get(ATTR_FILENAME)
        start_date_str = call.data.get(ATTR_START_DATE)
        end_date_str = call.data.get(ATTR_END_DATE)
        persons = call.data.get(ATTR_PERSONS)

        # Parse dates
        start_date = None
        end_date = None
        if start_date_str:
            try:
                start_date = datetime.fromisoformat(start_date_str)
            except ValueError:
                _LOGGER.warning(f"Invalid start_date format: {start_date_str}")

        if end_date_str:
            try:
                end_date = datetime.fromisoformat(end_date_str)
            except ValueError:
                _LOGGER.warning(f"Invalid end_date format: {end_date_str}")

        await tracker.async_export_excel(filename, start_date, end_date, persons)

    async def handle_clear_history(call: ServiceCall) -> None:
        """Handle the clear_history service call."""
        await tracker.async_clear_history()

    hass.services.async_register(
        DOMAIN, SERVICE_EXPORT_CSV, handle_export_csv, schema=SERVICE_EXPORT_CSV_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_EXPORT_EXCEL,
        handle_export_excel,
        schema=SERVICE_EXPORT_EXCEL_SCHEMA,
    )
    hass.services.async_register(DOMAIN, SERVICE_CLEAR_HISTORY, handle_clear_history)


async def async_register_http_views(
    hass: HomeAssistant, tracker: "PresenceTracker"
) -> None:
    """Register HTTP views for downloads."""
    hass.http.register_view(DownloadCSVView(tracker))
    hass.http.register_view(DownloadCSVFilteredView(tracker))
    hass.http.register_view(DownloadExcelView(tracker))
    hass.http.register_view(DashboardDataView(tracker))


class DownloadCSVView:
    """View to handle full CSV downloads (all data)."""

    url = HTTP_DOWNLOAD_PATH
    name = "api:suivi_presence:download"
    requires_auth = True

    def __init__(self, tracker: "PresenceTracker") -> None:
        self.tracker = tracker

    async def get(self, request) -> Any:
        from aiohttp import web

        csv_content = await self.tracker.async_get_csv_content()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"suivi_presence_complet_{timestamp}.csv"

        return web.Response(
            body=csv_content,
            content_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )


class DownloadCSVFilteredView:
    """View to handle filtered CSV downloads."""

    url = HTTP_DOWNLOAD_CSV_FILTERED
    name = "api:suivi_presence:download_csv"
    requires_auth = True

    def __init__(self, tracker: "PresenceTracker") -> None:
        self.tracker = tracker

    async def get(self, request) -> Any:
        from aiohttp import web

        # Get query parameters
        start_date_str = request.query.get("start_date")
        end_date_str = request.query.get("end_date")
        persons_str = request.query.get("persons")

        start_date = None
        end_date = None
        persons = None

        if start_date_str:
            try:
                start_date = datetime.fromisoformat(start_date_str)
            except ValueError:
                pass

        if end_date_str:
            try:
                end_date = datetime.fromisoformat(end_date_str)
            except ValueError:
                pass

        if persons_str:
            persons = [p.strip() for p in persons_str.split(",") if p.strip()]

        csv_content = await self.tracker.async_get_csv_content_filtered(
            start_date, end_date, persons
        )
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"suivi_presence_export_{timestamp}.csv"

        return web.Response(
            body=csv_content,
            content_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )


class DownloadExcelView:
    """View to handle Excel downloads with statistics."""

    url = HTTP_DOWNLOAD_EXCEL
    name = "api:suivi_presence:download_excel"
    requires_auth = True

    def __init__(self, tracker: "PresenceTracker") -> None:
        self.tracker = tracker

    async def get(self, request) -> Any:
        from aiohttp import web

        # Get query parameters
        start_date_str = request.query.get("start_date")
        end_date_str = request.query.get("end_date")
        persons_str = request.query.get("persons")

        start_date = None
        end_date = None
        persons = None

        if start_date_str:
            try:
                start_date = datetime.fromisoformat(start_date_str)
            except ValueError:
                pass

        if end_date_str:
            try:
                end_date = datetime.fromisoformat(end_date_str)
            except ValueError:
                pass

        if persons_str:
            persons = [p.strip() for p in persons_str.split(",") if p.strip()]

        excel_content = await self.tracker.async_get_excel_content(
            start_date, end_date, persons
        )
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"suivi_presence_rapport_{timestamp}.xlsx"

        return web.Response(
            body=excel_content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )


class DashboardDataView:
    """View to handle dashboard data requests."""

    url = HTTP_DATA_PATH
    name = "api:suivi_presence:data"
    requires_auth = True

    def __init__(self, tracker: "PresenceTracker") -> None:
        self.tracker = tracker

    async def get(self, request) -> Any:
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
        _LOGGER.info(f"CSV data file: {self.csv_path}")

        # Load existing CSV data (permanent storage)
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
        _LOGGER.info(f"Loaded {len(self._history)} historical records from CSV")

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
            self._person_states[entity_id] = {
                "zone": new_zone,
                "last_changed": new_state.last_changed,
                "friendly_name": new_state.attributes.get("friendly_name", entity_id),
            }
            return

        # Calculate duration in previous zone
        duration = None
        duration_seconds = None
        if entity_id in self._person_states:
            last_changed = self._person_states[entity_id].get("last_changed")
            if last_changed:
                duration = new_state.last_changed - last_changed
                duration_seconds = duration.total_seconds()

        # Record the change
        friendly_name = new_state.attributes.get("friendly_name", entity_id)
        await self._async_record_change(
            person=friendly_name,
            previous_zone=old_zone,
            new_zone=new_zone,
            timestamp=new_state.last_changed,
            duration=duration,
            duration_seconds=duration_seconds,
        )

        # Update tracked state
        self._person_states[entity_id] = {
            "zone": new_zone,
            "last_changed": new_state.last_changed,
            "friendly_name": friendly_name,
        }

        _LOGGER.debug(f"Person {friendly_name} moved from {old_zone} to {new_zone}")

    async def _async_record_change(
        self,
        person: str,
        previous_zone: str,
        new_zone: str,
        timestamp: datetime,
        duration: timedelta | None,
        duration_seconds: float | None,
    ) -> None:
        """Record a zone change to history and CSV."""
        duration_str = str(duration) if duration else ""

        record = {
            ATTR_TIMESTAMP: timestamp.isoformat(),
            ATTR_PERSON: person,
            ATTR_PREVIOUS_ZONE: previous_zone,
            ATTR_NEW_ZONE: new_zone,
            ATTR_DURATION: duration_str,
            ATTR_DURATION_SECONDS: duration_seconds if duration_seconds else "",
        }

        async with self._lock:
            self._history.append(record)
            await self._async_write_csv_row(record)

    async def _async_load_csv(self) -> None:
        """Load existing CSV data from permanent storage."""
        if not os.path.exists(self.csv_path):
            await self._async_create_csv()
            return

        try:

            def read_csv():
                records = []
                with open(self.csv_path, "r", encoding="utf-8", newline="") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        records.append(dict(row))
                return records

            self._history = await self.hass.async_add_executor_job(read_csv)
            _LOGGER.info(f"Loaded {len(self._history)} records from CSV")

        except Exception as e:
            _LOGGER.error(f"Error loading CSV: {e}")
            self._history = []

    async def _async_create_csv(self) -> None:
        """Create a new CSV file with headers."""

        def create_csv():
            dir_path = os.path.dirname(self.csv_path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
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
                        record.get(ATTR_TIMESTAMP, ""),
                        record.get(ATTR_PERSON, ""),
                        record.get(ATTR_PREVIOUS_ZONE, ""),
                        record.get(ATTR_NEW_ZONE, ""),
                        record.get(ATTR_DURATION, ""),
                        record.get(ATTR_DURATION_SECONDS, ""),
                    ]
                )

        await self.hass.async_add_executor_job(write_row)

    async def async_export_csv_filtered(
        self,
        filename: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        persons: list[str] | None = None,
    ) -> str:
        """Export filtered history to a CSV file."""
        if filename:
            export_path = os.path.join(self.hass.config.path(), filename)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_path = os.path.join(
                self.hass.config.path(), f"suivi_presence_export_{timestamp}.csv"
            )

        def write_export():
            csv_content = export_to_csv(self._history, start_date, end_date, persons)
            with open(export_path, "w", encoding="utf-8", newline="") as f:
                f.write(csv_content)

        await self.hass.async_add_executor_job(write_export)
        filtered_count = len(filter_history(self._history, start_date, end_date, persons))
        _LOGGER.info(f"Exported {filtered_count} records to {export_path}")
        return export_path

    async def async_export_excel(
        self,
        filename: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        persons: list[str] | None = None,
    ) -> str:
        """Export history to Excel with statistics."""
        if filename:
            if not filename.endswith(".xlsx"):
                filename += ".xlsx"
            export_path = os.path.join(self.hass.config.path(), filename)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_path = os.path.join(
                self.hass.config.path(), f"suivi_presence_rapport_{timestamp}.xlsx"
            )

        def write_export():
            excel_content = export_to_excel(self._history, start_date, end_date, persons)
            with open(export_path, "wb") as f:
                f.write(excel_content)

        await self.hass.async_add_executor_job(write_export)
        _LOGGER.info(f"Exported Excel report to {export_path}")
        return export_path

    async def async_clear_history(self) -> None:
        """Clear all recorded history (use with caution!)."""
        async with self._lock:
            self._history.clear()
            await self._async_create_csv()
        _LOGGER.warning("Cleared all presence history")

    async def async_get_csv_content(self) -> str:
        """Get full CSV content as string for download."""
        return export_to_csv(self._history)

    async def async_get_csv_content_filtered(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        persons: list[str] | None = None,
    ) -> str:
        """Get filtered CSV content as string for download."""
        return export_to_csv(self._history, start_date, end_date, persons)

    async def async_get_excel_content(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        persons: list[str] | None = None,
    ) -> bytes:
        """Get Excel content as bytes for download."""

        def generate():
            return export_to_excel(self._history, start_date, end_date, persons)

        return await self.hass.async_add_executor_job(generate)

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
                    "last_changed": (
                        data.get("last_changed").isoformat()
                        if data.get("last_changed")
                        else ""
                    ),
                }
            )

        # Recent history (last 50 entries)
        recent_history = self._history[-50:] if self._history else []

        # Statistics
        total_changes = len(self._history)
        persons_home = sum(
            1 for p in self._person_states.values() if p.get("zone") == STATE_HOME
        )
        persons_away = sum(
            1 for p in self._person_states.values() if p.get("zone") == STATE_NOT_HOME
        )

        # Date range info
        date_range = get_date_range_info(self._history)

        return {
            "current_status": current_status,
            "recent_history": recent_history,
            "statistics": {
                "total_changes": total_changes,
                "persons_home": persons_home,
                "persons_away": persons_away,
                "total_persons": len(self._person_states),
            },
            "data_range": date_range,
            "available_persons": get_unique_persons(self._history),
            "download_urls": {
                "csv_full": HTTP_DOWNLOAD_PATH,
                "csv_filtered": HTTP_DOWNLOAD_CSV_FILTERED,
                "excel": HTTP_DOWNLOAD_EXCEL,
            },
        }

    @property
    def history(self) -> list[dict]:
        """Return the history."""
        return self._history

    @property
    def person_states(self) -> dict[str, dict]:
        """Return current person states."""
        return self._person_states
