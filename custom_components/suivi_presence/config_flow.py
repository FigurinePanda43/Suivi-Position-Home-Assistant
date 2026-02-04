"""Config flow for Suivi de Présence integration."""
from __future__ import annotations

import logging
import os
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_CSV_PATH,
    CONF_SCAN_INTERVAL,
    DEFAULT_CSV_FILENAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


def get_default_csv_path(hass: HomeAssistant) -> str:
    """Get the default CSV path."""
    return os.path.join(hass.config.path(), DEFAULT_CSV_FILENAME)


class SuiviPresenceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Suivi de Présence."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        # Check if already configured
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            # Validate CSV path if provided
            csv_path = user_input.get(CONF_CSV_PATH, "")
            if csv_path:
                # Validate the path is writable
                try:
                    dir_path = os.path.dirname(csv_path)
                    if dir_path and not os.path.exists(dir_path):
                        errors[CONF_CSV_PATH] = "invalid_path"
                except Exception:
                    errors[CONF_CSV_PATH] = "invalid_path"

            if not errors:
                return self.async_create_entry(
                    title="Suivi de Présence",
                    data=user_input,
                )

        # Default values
        default_csv_path = get_default_csv_path(self.hass)

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=5,
                        max=300,
                        step=5,
                        unit_of_measurement="secondes",
                        mode=selector.NumberSelectorMode.SLIDER,
                    )
                ),
                vol.Optional(CONF_CSV_PATH, default=default_csv_path): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> SuiviPresenceOptionsFlowHandler:
        """Get the options flow for this handler."""
        return SuiviPresenceOptionsFlowHandler(config_entry)


class SuiviPresenceOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Suivi de Présence."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Get current values
        current_scan_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )

        # Get all person entities for selection
        persons = []
        for state in self.hass.states.async_all("person"):
            friendly_name = state.attributes.get("friendly_name", state.entity_id)
            persons.append(
                selector.SelectOptionDict(
                    value=state.entity_id,
                    label=friendly_name,
                )
            )

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=current_scan_interval
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=5,
                        max=300,
                        step=5,
                        unit_of_measurement="secondes",
                        mode=selector.NumberSelectorMode.SLIDER,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
            errors=errors,
        )
