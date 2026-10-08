"""Quick smoke test used while developing (kept: it documents the happy path)."""

from __future__ import annotations

import os

from homeassistant.core import HomeAssistant

from custom_components.suivi_presence.const import DOMAIN


async def test_setup_creates_sensors_and_csv(
    hass: HomeAssistant, setup_integration, csv_path: str
) -> None:
    """The entry loads, the tracker starts and the four sensors exist."""
    entry = setup_integration
    tracker = entry.runtime_data
    assert tracker.started
    assert os.path.exists(csv_path)
    ids = sorted(s.entity_id for s in hass.states.async_all("sensor"))
    assert ids == [
        "sensor.suivi_de_presence_personnes_a_domicile",
        "sensor.suivi_de_presence_personnes_absentes",
        "sensor.suivi_de_presence_suivi_presence",
        "sensor.suivi_de_presence_total_des_changements",
    ]
    assert hass.states.get("sensor.suivi_de_presence_suivi_presence").state == "2"
    assert hass.states.get("sensor.suivi_de_presence_personnes_a_domicile").state == "1"
    assert hass.states.get("sensor.suivi_de_presence_personnes_absentes").state == "1"
    assert hass.states.get("sensor.suivi_de_presence_total_des_changements").state == "0"
    assert hass.services.has_service(DOMAIN, "export_csv")
    assert hass.services.has_service(DOMAIN, "export_excel")
    assert hass.services.has_service(DOMAIN, "clear_history")
