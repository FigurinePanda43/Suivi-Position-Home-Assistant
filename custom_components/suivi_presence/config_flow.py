"""Config flow and options flow for Suivi de Présence."""

from __future__ import annotations

import os
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector
import voluptuous as vol

from .const import CONF_CSV_PATH, CONF_TRACKED_PERSONS, DEFAULT_CSV_FILENAME, DOMAIN


def default_csv_path(hass: HomeAssistant) -> str:
    """Return the default CSV path (inside the configuration directory)."""
    return hass.config.path(DEFAULT_CSV_FILENAME)


def normalise_csv_path(hass: HomeAssistant, value: str | None) -> str:
    """Return an absolute path, defaulting to the configuration directory."""
    path = (value or "").strip() or default_csv_path(hass)
    if not os.path.isabs(path):
        path = hass.config.path(path)
    return path


def validate_csv_path(path: str) -> str | None:
    """Check that the CSV path can be written. Returns an error key or None.

    Runs in the executor (file system access).
    """
    if not path.lower().endswith(".csv"):
        return "not_csv"
    directory = os.path.dirname(path) or "."
    if os.path.isdir(path):
        return "invalid_path"
    if os.path.exists(path):
        return None if os.access(path, os.W_OK) else "not_writable"
    if not os.path.isdir(directory):
        return "invalid_path"
    return None if os.access(directory, os.W_OK) else "not_writable"


def _schema(hass: HomeAssistant, *, include_path: bool = True) -> vol.Schema:
    fields: dict[Any, Any] = {
        vol.Optional(CONF_TRACKED_PERSONS, default=[]): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="person", multiple=True)
        ),
    }
    if include_path:
        fields[vol.Optional(CONF_CSV_PATH, default=default_csv_path(hass))] = (
            selector.TextSelector()
        )
    return vol.Schema(fields)


class SuiviPresenceConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial configuration."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the user step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        errors: dict[str, str] = {}
        if user_input is not None:
            csv_path = normalise_csv_path(self.hass, user_input.get(CONF_CSV_PATH))
            error = await self.hass.async_add_executor_job(validate_csv_path, csv_path)
            if error:
                errors[CONF_CSV_PATH] = error
            else:
                return self.async_create_entry(
                    title="Suivi de Présence",
                    data={CONF_CSV_PATH: csv_path},
                    options={CONF_TRACKED_PERSONS: user_input.get(CONF_TRACKED_PERSONS, [])},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(_schema(self.hass), user_input),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> SuiviPresenceOptionsFlow:
        """Return the options flow."""
        return SuiviPresenceOptionsFlow()


class SuiviPresenceOptionsFlow(OptionsFlow):
    """Let the user change the tracked persons and the CSV path."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}
        if user_input is not None:
            csv_path = normalise_csv_path(self.hass, user_input.get(CONF_CSV_PATH))
            error = await self.hass.async_add_executor_job(validate_csv_path, csv_path)
            if error:
                errors[CONF_CSV_PATH] = error
            else:
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_TRACKED_PERSONS: user_input.get(CONF_TRACKED_PERSONS, []),
                        CONF_CSV_PATH: csv_path,
                    },
                )

        entry = self.config_entry
        current = {
            CONF_TRACKED_PERSONS: entry.options.get(
                CONF_TRACKED_PERSONS, entry.data.get(CONF_TRACKED_PERSONS, [])
            ),
            CONF_CSV_PATH: entry.options.get(
                CONF_CSV_PATH, entry.data.get(CONF_CSV_PATH, default_csv_path(self.hass))
            ),
        }
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                _schema(self.hass), user_input or current
            ),
            errors=errors,
        )
