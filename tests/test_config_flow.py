"""Config flow and options flow."""

from __future__ import annotations

import os

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.suivi_presence.const import CONF_CSV_PATH, CONF_TRACKED_PERSONS, DOMAIN


async def test_user_flow_creates_entry_with_defaults(hass: HomeAssistant, setup_deps: None) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Suivi de Présence"
    assert result["data"] == {CONF_CSV_PATH: hass.config.path("suivi_presence_data.csv")}
    assert result["options"] == {CONF_TRACKED_PERSONS: []}
    assert os.path.exists(hass.config.path("suivi_presence_data.csv"))


async def test_user_flow_custom_path_and_persons(
    hass: HomeAssistant, setup_deps: None, tmp_path
) -> None:
    hass.states.async_set("person.jean", "home", {"friendly_name": "Jean"})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_CSV_PATH: "data/presence.csv", CONF_TRACKED_PERSONS: ["person.jean"]},
    )
    # Relative paths are resolved against the configuration folder; the folder must exist.
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_CSV_PATH: "invalid_path"}

    os.makedirs(hass.config.path("data"))
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_CSV_PATH: "data/presence.csv", CONF_TRACKED_PERSONS: ["person.jean"]},
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_CSV_PATH] == hass.config.path("data/presence.csv")
    assert result["options"][CONF_TRACKED_PERSONS] == ["person.jean"]


async def test_user_flow_rejects_non_csv(hass: HomeAssistant, setup_deps: None) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_CSV_PATH: "data.txt"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_CSV_PATH: "not_csv"}


async def test_single_instance(hass: HomeAssistant, setup_integration: MockConfigEntry) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_options_flow(
    hass: HomeAssistant, setup_integration: MockConfigEntry, csv_path: str
) -> None:
    """Regression: opening the options used to crash with TypeError."""
    result = await hass.config_entries.options.async_init(setup_integration.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_TRACKED_PERSONS: ["person.marie"], CONF_CSV_PATH: csv_path}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert setup_integration.options == {
        CONF_TRACKED_PERSONS: ["person.marie"],
        CONF_CSV_PATH: csv_path,
    }
    # The entry was reloaded with the new option.
    assert hass.states.get("sensor.suivi_de_presence_suivi_presence").state == "1"
    assert setup_integration.runtime_data.tracked_persons == {"person.marie"}


async def test_options_flow_invalid_path(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    result = await hass.config_entries.options.async_init(setup_integration.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_TRACKED_PERSONS: [], CONF_CSV_PATH: "/nonexistent/folder/x.csv"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_CSV_PATH: "invalid_path"}
