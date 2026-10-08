"""WebSocket API used by the Lovelace card.

* ``suivi_presence/overview``: live state of every tracked person;
* ``suivi_presence/history``: transitions and per-zone summary for a period.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .const import DOMAIN, MAX_HISTORY_RESULTS, WS_HISTORY, WS_OVERVIEW
from .export import get_date_range_info
from .http import build_history_payload
from .tracker import async_get_tracker
from .util import parse_user_datetime


@websocket_api.websocket_command({vol.Required("type"): WS_OVERVIEW})
@callback
def ws_overview(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Return the live overview."""
    tracker = async_get_tracker(hass)
    if tracker is None:
        connection.send_error(msg["id"], "not_loaded", "Intégration Suivi de Présence non chargée")
        return
    payload = tracker.overview()
    payload["excel_available"] = hass.data.get(DOMAIN, {}).get("excel_available", False)
    payload["version"] = hass.data.get(DOMAIN, {}).get("version")
    payload["data_range"] = get_date_range_info(tracker.history)
    connection.send_result(msg["id"], payload)


@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_HISTORY,
        vol.Optional("start"): cv.string,
        vol.Optional("end"): cv.string,
        vol.Optional("persons"): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional("limit", default=500): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=MAX_HISTORY_RESULTS)
        ),
    }
)
@callback
def ws_history(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Return filtered transitions and the zone summary of the period."""
    tracker = async_get_tracker(hass)
    if tracker is None:
        connection.send_error(msg["id"], "not_loaded", "Intégration Suivi de Présence non chargée")
        return
    start_raw = msg.get("start")
    end_raw = msg.get("end")
    start = parse_user_datetime(start_raw)
    end = parse_user_datetime(end_raw, end_of_day=True)
    if (start_raw and start is None) or (end_raw and end is None):
        connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT, "Date invalide")
        return
    if start and end and end < start:
        connection.send_error(
            msg["id"], websocket_api.ERR_INVALID_FORMAT, "Date de fin antérieure à la date de début"
        )
        return
    persons = msg.get("persons") or None
    connection.send_result(
        msg["id"],
        build_history_payload(tracker, start=start, end=end, persons=persons, limit=msg["limit"]),
    )


@callback
def async_register_websocket_commands(hass: HomeAssistant) -> None:
    """Register the websocket commands (once)."""
    websocket_api.async_register_command(hass, ws_overview)
    websocket_api.async_register_command(hass, ws_history)
