"""WebSocket commands used by the Lovelace card."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.typing import WebSocketGenerator


async def test_overview(
    hass: HomeAssistant, setup_integration: MockConfigEntry, hass_ws_client: WebSocketGenerator
) -> None:
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "suivi_presence/overview"})
    msg = await client.receive_json()
    assert msg["success"], msg
    result = msg["result"]
    assert result["tracking"] is True
    assert result["version"] == "1.0.0"
    assert result["excel_available"] is True
    persons = {p["entity_id"]: p for p in result["persons"]}
    assert set(persons) == {"person.jean", "person.marie"}
    assert persons["person.jean"]["zone"] == "home"
    assert persons["person.jean"]["available"] is True
    assert persons["person.jean"]["since"] is not None
    assert persons["person.marie"]["latitude"] == 48.85
    assert persons["person.marie"]["gps_accuracy"] == 25
    assert persons["person.marie"]["source"] == "device_tracker.phone_marie"
    assert result["total_records"] == 0
    assert result["data_range"]["total_records"] == 0


async def test_history_with_period_and_summary(
    hass: HomeAssistant, setup_integration: MockConfigEntry, hass_ws_client: WebSocketGenerator
) -> None:
    hass.states.async_set("person.jean", "Travail", {"friendly_name": "Jean"})
    await hass.async_block_till_done()
    hass.states.async_set("person.jean", "home", {"friendly_name": "Jean"})
    await hass.async_block_till_done()

    client = await hass_ws_client(hass)
    today = dt_util.now().strftime("%Y-%m-%d")
    await client.send_json({"id": 1, "type": "suivi_presence/history", "start": today, "limit": 1})
    msg = await client.receive_json()
    assert msg["success"], msg
    result = msg["result"]
    assert result["total"] == 2
    assert result["truncated"] is True
    assert len(result["records"]) == 1
    record = result["records"][0]
    assert record["new_zone"] == "home"  # newest first
    assert record["timestamp_utc"].endswith("+00:00")
    assert isinstance(record["duration_seconds"], int)
    summary = result["summary"]
    assert "Jean" in summary
    assert set(summary["Jean"]) >= {"home", "Travail"}
    assert summary["Jean"]["home"]["ongoing"] is True
    assert summary["Jean"]["Travail"]["visits"] == 1
    # Marie is away all day: her ongoing stay counts even without a record.
    assert summary["Marie"]["not_home"]["ongoing"] is True

    await client.send_json(
        {"id": 2, "type": "suivi_presence/history", "persons": ["person.marie"], "start": today}
    )
    msg = await client.receive_json()
    assert msg["success"]
    assert msg["result"]["total"] == 0
    assert set(msg["result"]["summary"]) == {"Marie"}


async def test_history_invalid_dates(
    hass: HomeAssistant, setup_integration: MockConfigEntry, hass_ws_client: WebSocketGenerator
) -> None:
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "suivi_presence/history", "start": "31/12/2025"})
    msg = await client.receive_json()
    assert not msg["success"]
    assert msg["error"]["code"] == "invalid_format"
    await client.send_json(
        {"id": 2, "type": "suivi_presence/history", "start": "2025-02-01", "end": "2025-01-01"}
    )
    msg = await client.receive_json()
    assert not msg["success"]


async def test_commands_when_not_loaded(
    hass: HomeAssistant, setup_integration: MockConfigEntry, hass_ws_client: WebSocketGenerator
) -> None:
    assert await hass.config_entries.async_unload(setup_integration.entry_id)
    await hass.async_block_till_done()
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "suivi_presence/overview"})
    msg = await client.receive_json()
    assert not msg["success"]
    assert msg["error"]["code"] == "not_loaded"
