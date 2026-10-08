"""Shared fixtures."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

# Import the repository's ``custom_components`` namespace package BEFORE the
# ``hass`` fixture mounts the plugin's own testing_config/custom_components
# (a regular package that would otherwise shadow ours).
from custom_components.suivi_presence.const import CONF_CSV_PATH, DOMAIN  # noqa: F401


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading custom integrations in every test."""


@pytest.fixture
def csv_path(tmp_path: Path) -> str:
    """Path of the CSV storage used by a test."""
    return str(tmp_path / "suivi_presence_data.csv")


@pytest.fixture
async def setup_deps(hass: HomeAssistant, tmp_path: Path) -> None:
    """Set up the Home Assistant components the integration depends on.

    The configuration directory is redirected to a temporary folder (exports are
    written there) and the time zone is set to Europe/Paris so that local-time
    semantics are really exercised.
    """
    hass.config.config_dir = str(tmp_path)
    await hass.config.async_set_time_zone("Europe/Paris")
    assert await async_setup_component(hass, "homeassistant", {})
    assert await async_setup_component(hass, "http", {})
    assert await async_setup_component(hass, "frontend", {})
    assert await async_setup_component(hass, "websocket_api", {})
    assert await async_setup_component(hass, "person", {})
    await hass.async_block_till_done()


@pytest.fixture
async def config_entry(hass: HomeAssistant, csv_path: str, setup_deps: None) -> MockConfigEntry:
    """Create (but do not set up) a config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Suivi de Présence",
        data={CONF_CSV_PATH: csv_path},
        options={},
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
async def setup_integration(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> AsyncGenerator[MockConfigEntry]:
    """Set up the integration with two persons already known to Home Assistant."""
    hass.states.async_set("person.jean", "home", {"friendly_name": "Jean"})
    hass.states.async_set(
        "person.marie",
        "not_home",
        {
            "friendly_name": "Marie",
            "latitude": 48.85,
            "longitude": 2.35,
            "gps_accuracy": 25,
            "source": "device_tracker.phone_marie",
        },
    )
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    yield config_entry
