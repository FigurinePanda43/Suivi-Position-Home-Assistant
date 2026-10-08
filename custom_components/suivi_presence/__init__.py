"""Suivi de Présence — Home Assistant integration.

Records every zone change of ``person.*`` entities into a permanent CSV file
(Home Assistant's own recorder only keeps a few days) and provides a Lovelace
card, HTTP downloads (CSV / Excel), websocket commands and services.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import (
    CoreState,
    Event,
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import ServiceValidationError, Unauthorized
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration
import voluptuous as vol

from .const import (
    ATTR_DELIMITER,
    ATTR_END_DATE,
    ATTR_FILENAME,
    ATTR_PERSONS,
    ATTR_START_DATE,
    CARD_FILENAME,
    CONF_CSV_PATH,
    CONF_TRACKED_PERSONS,
    CSV_DELIMITERS,
    DEFAULT_CSV_FILENAME,
    DOMAIN,
    PLATFORMS,
    SERVICE_CLEAR_HISTORY,
    SERVICE_EXPORT_CSV,
    SERVICE_EXPORT_EXCEL,
    STATIC_URL_BASE,
)
from .export import export_to_csv, export_to_excel, filter_history
from .http import async_register_views
from .tracker import DATA_TRACKERS, PresenceTracker, async_get_tracker
from .util import parse_user_datetime
from .websocket import async_register_websocket_commands

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

DATA_VERSION = "version"

type SuiviPresenceConfigEntry = ConfigEntry[PresenceTracker]

_FILTER_FIELDS = {
    vol.Optional(ATTR_START_DATE): cv.string,
    vol.Optional(ATTR_END_DATE): cv.string,
    vol.Optional(ATTR_PERSONS): vol.All(cv.ensure_list, [cv.string]),
}

SERVICE_EXPORT_CSV_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_FILENAME): cv.string,
        vol.Optional(ATTR_DELIMITER, default=","): vol.In(CSV_DELIMITERS),
        **_FILTER_FIELDS,
    }
)
SERVICE_EXPORT_EXCEL_SCHEMA = vol.Schema({vol.Optional(ATTR_FILENAME): cv.string, **_FILTER_FIELDS})


# --------------------------------------------------------------------------- #
# Domain-level setup (runs once per Home Assistant start)
# --------------------------------------------------------------------------- #


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register everything that must exist exactly once: HTTP views, websocket
    commands, static files, the Lovelace resource and the services."""
    integration = await async_get_integration(hass, DOMAIN)
    version = integration.version or "0"
    hass.data[DOMAIN] = {DATA_TRACKERS: {}, DATA_VERSION: str(version)}

    await _async_register_frontend(hass, str(version))
    async_register_views(hass)
    async_register_websocket_commands(hass)
    _async_register_services(hass)
    return True


async def _async_register_frontend(hass: HomeAssistant, version: str) -> None:
    """Serve the card and load it automatically on every dashboard."""
    www_path = Path(__file__).parent / "www"
    if not www_path.is_dir():
        _LOGGER.error("Dossier www introuvable : %s", www_path)
        return

    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(STATIC_URL_BASE, str(www_path), cache_headers=False),
            # Legacy location used by versions <= 0.1.1 (manual resource).
            StaticPathConfig(f"/local{STATIC_URL_BASE}", str(www_path), cache_headers=False),
        ]
    )
    # Cache busting: the version is part of the URL, so browsers reload the
    # card after each update without the user clearing anything.
    add_extra_js_url(hass, f"{STATIC_URL_BASE}/{CARD_FILENAME}?v={version}")
    _LOGGER.debug("Carte Lovelace servie depuis %s%s", STATIC_URL_BASE, f"/{CARD_FILENAME}")


# --------------------------------------------------------------------------- #
# Config entry lifecycle
# --------------------------------------------------------------------------- #


def _csv_path_for_entry(hass: HomeAssistant, entry: ConfigEntry) -> str:
    path = (
        entry.options.get(CONF_CSV_PATH)
        or entry.data.get(CONF_CSV_PATH)
        or hass.config.path(DEFAULT_CSV_FILENAME)
    )
    if not os.path.isabs(path):
        path = hass.config.path(path)
    return path


async def async_setup_entry(hass: HomeAssistant, entry: SuiviPresenceConfigEntry) -> bool:
    """Set up the tracker for a config entry."""
    tracked = entry.options.get(CONF_TRACKED_PERSONS, entry.data.get(CONF_TRACKED_PERSONS, []))
    tracker = PresenceTracker(hass, _csv_path_for_entry(hass, entry), list(tracked or []))

    entry.runtime_data = tracker
    hass.data[DOMAIN][DATA_TRACKERS][entry.entry_id] = tracker

    async def _start(_event: Event | None = None) -> None:
        await tracker.async_start()

    if hass.state is CoreState.running:
        await _start()
    else:
        # During boot (CoreState.starting) person states are not reliable yet:
        # device trackers are still being restored. Wait for the STARTED event.
        entry.async_on_unload(hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _start))

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: SuiviPresenceConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        tracker: PresenceTracker | None = hass.data[DOMAIN][DATA_TRACKERS].pop(entry.entry_id, None)
        if tracker is not None:
            await tracker.async_stop()
    return unload_ok


# --------------------------------------------------------------------------- #
# Services
# --------------------------------------------------------------------------- #


def _require_tracker(hass: HomeAssistant) -> PresenceTracker:
    tracker = async_get_tracker(hass)
    if tracker is None:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="not_loaded")
    return tracker


def _parse_filters(call: ServiceCall) -> tuple[Any, Any, list[str] | None]:
    start_raw = call.data.get(ATTR_START_DATE)
    end_raw = call.data.get(ATTR_END_DATE)
    start = parse_user_datetime(start_raw)
    end = parse_user_datetime(end_raw, end_of_day=True)
    if (start_raw and start is None) or (end_raw and end is None):
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="invalid_date")
    if start and end and end < start:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="invalid_range")
    persons = call.data.get(ATTR_PERSONS) or None
    return start, end, persons


def _export_path(
    hass: HomeAssistant, filename: str | None, default_stem: str, extension: str
) -> str:
    """Resolve the output path of an export, confined to the configuration directory."""
    from homeassistant.util import dt as dt_util  # noqa: PLC0415

    if not filename:
        filename = f"{default_stem}_{dt_util.now().strftime('%Y%m%d_%H%M%S')}{extension}"
    if not filename.lower().endswith(extension):
        filename = f"{filename}{extension}"
    config_dir = os.path.realpath(hass.config.config_dir)
    path = os.path.realpath(hass.config.path(filename))
    if os.path.commonpath([config_dir, path]) != config_dir:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="invalid_path")
    return path


def _write_file(path: str, content: bytes) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(content)


async def _async_require_admin(hass: HomeAssistant, call: ServiceCall) -> None:
    """Refuse the call if it comes from a non-administrator user."""
    if call.context.user_id is None:
        return  # automation / system call
    user = await hass.auth.async_get_user(call.context.user_id)
    if user is None or not user.is_admin:
        raise Unauthorized(context=call.context)


def _async_register_services(hass: HomeAssistant) -> None:
    async def handle_export_csv(call: ServiceCall) -> ServiceResponse:
        tracker = _require_tracker(hass)
        start, end, persons = _parse_filters(call)
        path = _export_path(hass, call.data.get(ATTR_FILENAME), "suivi_presence_export", ".csv")
        content = export_to_csv(
            tracker.history, start, end, persons, delimiter=call.data[ATTR_DELIMITER], bom=True
        )
        await hass.async_add_executor_job(_write_file, path, content.encode("utf-8"))
        records = len(filter_history(tracker.history, start, end, persons))
        _LOGGER.info("Export CSV : %d enregistrement(s) -> %s", records, path)
        return {"path": path, "records": records}

    async def handle_export_excel(call: ServiceCall) -> ServiceResponse:
        tracker = _require_tracker(hass)
        start, end, persons = _parse_filters(call)
        path = _export_path(hass, call.data.get(ATTR_FILENAME), "suivi_presence_rapport", ".xlsx")
        content = await hass.async_add_executor_job(
            lambda: export_to_excel(
                tracker.history, tracker.current_states, start=start, end=end, persons=persons
            )
        )
        await hass.async_add_executor_job(_write_file, path, content)
        records = len(filter_history(tracker.history, start, end, persons))
        _LOGGER.info("Export Excel : %d enregistrement(s) -> %s", records, path)
        return {"path": path, "records": records}

    async def handle_clear_history(call: ServiceCall) -> ServiceResponse:
        tracker = _require_tracker(hass)
        await _async_require_admin(hass, call)
        backup = await tracker.async_clear_history()
        return {"backup": backup}

    hass.services.async_register(
        DOMAIN,
        SERVICE_EXPORT_CSV,
        handle_export_csv,
        schema=SERVICE_EXPORT_CSV_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_EXPORT_EXCEL,
        handle_export_excel,
        schema=SERVICE_EXPORT_EXCEL_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEAR_HISTORY,
        handle_clear_history,
        schema=vol.Schema({}),
        supports_response=SupportsResponse.OPTIONAL,
    )
