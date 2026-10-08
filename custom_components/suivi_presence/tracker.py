"""Presence tracker: listens to ``person.*`` state changes and records zone transitions.

Storage is an append-only CSV file (see ``const.CSV_HEADERS``). The whole file is
kept in memory as a list of dict records (a few thousand rows per year at most).
"""

from __future__ import annotations

import asyncio
import csv
from datetime import datetime
import logging
import os
import shutil
from typing import Any

from homeassistant.const import (
    ATTR_FRIENDLY_NAME,
    EVENT_STATE_CHANGED,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import (
    CALLBACK_TYPE,
    Event,
    EventStateChangedData,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_DURATION,
    ATTR_DURATION_SECONDS,
    ATTR_NEW_ZONE,
    ATTR_PERSON,
    ATTR_PERSON_ENTITY_ID,
    ATTR_PREVIOUS_ZONE,
    ATTR_TIMESTAMP,
    CSV_HEADERS,
)
from .stats import CurrentState
from .util import format_duration_hms, format_timestamp, parse_timestamp

_LOGGER = logging.getLogger(__name__)

PERSON_DOMAIN = "person"
_INVALID_STATES = (STATE_UNKNOWN, STATE_UNAVAILABLE)


def _friendly_name(state: State) -> str:
    return str(state.attributes.get(ATTR_FRIENDLY_NAME) or state.entity_id)


class PresenceTracker:
    """Track zone changes of persons and persist them to CSV."""

    def __init__(
        self,
        hass: HomeAssistant,
        csv_path: str,
        tracked_persons: list[str] | None = None,
    ) -> None:
        """Initialise the tracker (does not start listening yet)."""
        self.hass = hass
        self.csv_path = csv_path
        self._tracked: set[str] = set(tracked_persons or [])
        self._history: list[dict[str, Any]] = []
        self._states: dict[str, CurrentState] = {}
        self._lock = asyncio.Lock()
        self._unsub: CALLBACK_TYPE | None = None
        self._listeners: list[CALLBACK_TYPE] = []
        self._started = False
        self.migrated_from: str | None = None
        self.load_error: str | None = None

    # ------------------------------------------------------------------ #
    # Public read API
    # ------------------------------------------------------------------ #

    @property
    def history(self) -> list[dict[str, Any]]:
        """All recorded transitions, oldest first."""
        return self._history

    @property
    def started(self) -> bool:
        """True once the tracker has loaded the CSV and listens to events."""
        return self._started

    @property
    def tracked_persons(self) -> set[str]:
        """Configured person entity ids (empty set = every person)."""
        return set(self._tracked)

    @property
    def current_states(self) -> list[CurrentState]:
        """Current zone of each tracked person, sorted by name."""
        return sorted(self._states.values(), key=lambda s: s.person.casefold())

    def is_tracked(self, entity_id: str) -> bool:
        """Return True if the entity is a person this tracker follows."""
        if not entity_id.startswith(f"{PERSON_DOMAIN}."):
            return False
        return not self._tracked or entity_id in self._tracked

    @callback
    def async_add_listener(self, listener: CALLBACK_TYPE) -> CALLBACK_TYPE:
        """Register a callback fired after each change (new record, new state)."""
        self._listeners.append(listener)

        @callback
        def remove() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return remove

    @callback
    def _async_notify(self) -> None:
        for listener in list(self._listeners):
            listener()

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    async def async_start(self) -> None:
        """Load the CSV, reconcile with current states and start listening."""
        _LOGGER.debug("Starting presence tracker, CSV file: %s", self.csv_path)
        await self.hass.async_add_executor_job(self._load_csv)
        await self._async_reconcile()
        self._unsub = self.hass.bus.async_listen(
            EVENT_STATE_CHANGED,
            self._async_state_changed,
            event_filter=self._async_event_filter,
        )
        self._started = True
        _LOGGER.info(
            "Suivi de Présence actif : %d personne(s) suivie(s), %d changement(s) chargé(s) depuis %s",
            len(self._states),
            len(self._history),
            self.csv_path,
        )
        self._async_notify()

    async def async_stop(self) -> None:
        """Stop listening to state changes."""
        if self._unsub is not None:
            self._unsub()
            self._unsub = None
        self._started = False
        _LOGGER.debug("Presence tracker stopped")

    # ------------------------------------------------------------------ #
    # Event handling
    # ------------------------------------------------------------------ #

    @callback
    def _async_event_filter(self, data: EventStateChangedData) -> bool:
        return self.is_tracked(data["entity_id"])

    @callback
    def _async_state_changed(self, event: Event[EventStateChangedData]) -> None:
        self.hass.async_create_task(self._async_handle_state_change(event.data))

    async def _async_handle_state_change(self, data: EventStateChangedData) -> None:
        entity_id = data["entity_id"]
        new_state = data["new_state"]
        old_state = data["old_state"]

        if new_state is None:
            # Person removed from Home Assistant.
            if self._states.pop(entity_id, None) is not None:
                self._async_notify()
            return

        name = _friendly_name(new_state)
        current = self._states.get(entity_id)

        if new_state.state in _INVALID_STATES:
            # Keep the last known zone, just flag the person as unavailable.
            if current is not None and current.extra.get("available", True):
                current.extra["available"] = False
                self._async_notify()
            return

        new_zone = new_state.state
        old_zone = old_state.state if old_state else None

        if current is None:
            # First real state seen for this person (created after startup, or
            # unknown at startup). Nothing to record yet.
            self._states[entity_id] = CurrentState(
                person=name,
                zone=new_zone,
                since=new_state.last_changed,
                entity_id=entity_id,
                extra={"available": True},
            )
            self._async_notify()
            return

        current.extra["available"] = True
        current.person = name

        if current.zone == new_zone:
            # Attribute-only update (GPS refresh) or recovery from unavailable
            # in the same zone: nothing to record.
            if old_zone in _INVALID_STATES:
                self._async_notify()
            return

        timestamp = new_state.last_changed
        duration = (timestamp - current.since).total_seconds() if current.since else None
        await self._async_record(
            person=name,
            entity_id=entity_id,
            previous_zone=current.zone,
            new_zone=new_zone,
            timestamp=timestamp,
            duration_seconds=duration,
        )
        self._states[entity_id] = CurrentState(
            person=name,
            zone=new_zone,
            since=timestamp,
            entity_id=entity_id,
            extra={"available": True},
        )
        _LOGGER.debug("%s: %s -> %s", name, current.zone, new_zone)
        self._async_notify()

    # ------------------------------------------------------------------ #
    # Startup reconciliation
    # ------------------------------------------------------------------ #

    async def _async_reconcile(self) -> None:
        """Rebuild current states from the CSV and record transitions missed while HA was down."""
        now = dt_util.utcnow()
        last_by_entity: dict[str, dict[str, Any]] = {}
        last_by_name: dict[str, dict[str, Any]] = {}
        for record in self._history:
            if record.get(ATTR_PERSON_ENTITY_ID):
                last_by_entity[record[ATTR_PERSON_ENTITY_ID]] = record
            if record.get(ATTR_PERSON):
                last_by_name[record[ATTR_PERSON]] = record

        for state in self.hass.states.async_all(PERSON_DOMAIN):
            entity_id = state.entity_id
            if not self.is_tracked(entity_id):
                continue
            name = _friendly_name(state)
            if state.state in _INVALID_STATES:
                # Wait for a real state; the event handler will pick it up.
                continue

            last = last_by_entity.get(entity_id) or last_by_name.get(name)
            since: datetime | None = state.last_changed

            if last is not None:
                last_ts = parse_timestamp(last.get(ATTR_TIMESTAMP))
                last_zone = last.get(ATTR_NEW_ZONE) or ""
                if last_zone == state.state:
                    # Still in the zone recorded last: the stay started at that record.
                    if last_ts is not None and last_ts <= now:
                        since = last_ts
                elif last_zone:
                    # Zone changed while Home Assistant was not running: record it,
                    # dated at the best known moment (the person's last change).
                    timestamp = state.last_changed
                    if last_ts is not None and timestamp <= last_ts:
                        timestamp = now
                    duration = (timestamp - last_ts).total_seconds() if last_ts else None
                    _LOGGER.info(
                        "Changement de zone détecté pendant l'arrêt de Home Assistant : %s %s -> %s",
                        name,
                        last_zone,
                        state.state,
                    )
                    await self._async_record(
                        person=name,
                        entity_id=entity_id,
                        previous_zone=last_zone,
                        new_zone=state.state,
                        timestamp=timestamp,
                        duration_seconds=duration,
                    )
                    since = timestamp

            self._states[entity_id] = CurrentState(
                person=name,
                zone=state.state,
                since=since,
                entity_id=entity_id,
                extra={"available": True},
            )

    # ------------------------------------------------------------------ #
    # Recording
    # ------------------------------------------------------------------ #

    async def _async_record(
        self,
        *,
        person: str,
        entity_id: str,
        previous_zone: str,
        new_zone: str,
        timestamp: datetime,
        duration_seconds: float | None,
    ) -> dict[str, Any]:
        record = {
            ATTR_TIMESTAMP: format_timestamp(timestamp),
            ATTR_PERSON: person,
            ATTR_PREVIOUS_ZONE: previous_zone,
            ATTR_NEW_ZONE: new_zone,
            ATTR_DURATION: format_duration_hms(duration_seconds),
            ATTR_DURATION_SECONDS: (
                "" if duration_seconds is None else str(int(round(duration_seconds)))
            ),
            ATTR_PERSON_ENTITY_ID: entity_id,
        }
        async with self._lock:
            self._history.append(record)
            try:
                await self.hass.async_add_executor_job(self._append_row, record)
            except OSError as err:
                _LOGGER.error("Impossible d'écrire dans %s : %s", self.csv_path, err)
        return record

    # ------------------------------------------------------------------ #
    # CSV file handling (executor only)
    # ------------------------------------------------------------------ #

    def _create_csv(self) -> None:
        directory = os.path.dirname(self.csv_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self.csv_path, "w", encoding="utf-8", newline="") as handle:
            csv.writer(handle).writerow(CSV_HEADERS)

    def _append_row(self, record: dict[str, Any]) -> None:
        if not os.path.exists(self.csv_path):
            self._create_csv()
        with open(self.csv_path, "a", encoding="utf-8", newline="") as handle:
            csv.writer(handle).writerow([record.get(h, "") for h in CSV_HEADERS])

    def _backup_path(self, tag: str) -> str:
        stamp = dt_util.now().strftime("%Y%m%d-%H%M%S")
        return f"{self.csv_path}.bak-{tag}-{stamp}"

    def _load_csv(self) -> None:
        """Load the CSV into memory, migrating legacy headers if needed."""
        self.load_error = None
        if not os.path.exists(self.csv_path):
            self._create_csv()
            self._history = []
            return

        try:
            with open(self.csv_path, encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.reader(handle))
        except (OSError, csv.Error) as err:
            self.load_error = str(err)
            _LOGGER.error("Impossible de lire %s : %s", self.csv_path, err)
            self._history = []
            return

        if not rows:
            self._create_csv()
            self._history = []
            return

        header = [cell.strip() for cell in rows[0]]
        records: list[dict[str, Any]] = []
        for row in rows[1:]:
            if not row or all(not cell.strip() for cell in row):
                continue
            raw = {header[i]: (row[i] if i < len(row) else "") for i in range(len(header))}
            records.append({h: raw.get(h, "") for h in CSV_HEADERS})
        self._history = records

        if header == CSV_HEADERS:
            return

        if header == CSV_HEADERS[: len(header)]:
            # Known legacy layout: add the new columns, keeping a backup first.
            backup = self._backup_path("migration")
            shutil.copy2(self.csv_path, backup)
            with open(self.csv_path, "w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(CSV_HEADERS)
                for record in records:
                    writer.writerow([record.get(h, "") for h in CSV_HEADERS])
            self.migrated_from = ",".join(header)
            _LOGGER.warning(
                "Fichier CSV migré vers le format 1.0.0 (%d lignes). Sauvegarde : %s",
                len(records),
                backup,
            )
        else:
            self.load_error = f"En-tête CSV inattendu : {header}"
            _LOGGER.error(
                "En-tête CSV inattendu dans %s : %s. Les colonnes connues sont chargées, "
                "les nouvelles lignes sont écrites au format 1.0.0.",
                self.csv_path,
                header,
            )

    def _backup_and_recreate(self) -> str:
        backup = self._backup_path("avant-effacement")
        if os.path.exists(self.csv_path):
            shutil.copy2(self.csv_path, backup)
        self._create_csv()
        return backup

    # ------------------------------------------------------------------ #
    # Maintenance
    # ------------------------------------------------------------------ #

    async def async_clear_history(self) -> str:
        """Clear the history after backing up the CSV. Returns the backup path."""
        async with self._lock:
            backup = await self.hass.async_add_executor_job(self._backup_and_recreate)
            self._history = []
        _LOGGER.warning("Historique effacé. Sauvegarde conservée : %s", backup)
        self._async_notify()
        return backup

    # ------------------------------------------------------------------ #
    # Snapshots for the API
    # ------------------------------------------------------------------ #

    def overview(self) -> dict[str, Any]:
        """Return the live state of each tracked person for the dashboard."""
        persons: list[dict[str, Any]] = []
        for current in self.current_states:
            ha_state = self.hass.states.get(current.entity_id) if current.entity_id else None
            attributes = ha_state.attributes if ha_state else {}
            persons.append(
                {
                    "entity_id": current.entity_id,
                    "name": current.person,
                    "zone": current.zone,
                    "since": current.since.isoformat() if current.since else None,
                    "available": bool(
                        ha_state is not None
                        and ha_state.state not in _INVALID_STATES
                        and current.extra.get("available", True)
                    ),
                    "latitude": attributes.get("latitude"),
                    "longitude": attributes.get("longitude"),
                    "gps_accuracy": attributes.get("gps_accuracy"),
                    "source": attributes.get("source"),
                    "picture": attributes.get("entity_picture"),
                    "last_updated": ha_state.last_updated.isoformat() if ha_state else None,
                }
            )
        last = self._history[-1] if self._history else None
        return {
            "tracking": self._started,
            "persons": persons,
            "total_records": len(self._history),
            "last_record": dict(last) if last else None,
            "csv_path": self.csv_path,
            "load_error": self.load_error,
        }


DATA_TRACKERS = "trackers"


@callback
def async_get_tracker(hass: HomeAssistant) -> PresenceTracker | None:
    """Return the tracker of the (single) loaded config entry, if any."""
    from .const import DOMAIN  # noqa: PLC0415  (avoid import cycle at module import)

    trackers: dict[str, PresenceTracker] = hass.data.get(DOMAIN, {}).get(DATA_TRACKERS, {})
    return next(iter(trackers.values()), None)
