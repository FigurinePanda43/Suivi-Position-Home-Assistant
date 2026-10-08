"""Services: exports written to the configuration folder, admin-only clearing."""

from __future__ import annotations

import os

from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError, Unauthorized
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, MockUser

from custom_components.suivi_presence.const import DOMAIN


async def _make_history(hass: HomeAssistant) -> None:
    hass.states.async_set("person.jean", "Travail", {"friendly_name": "Jean"})
    await hass.async_block_till_done()
    hass.states.async_set("person.marie", "home", {"friendly_name": "Marie"})
    await hass.async_block_till_done()


async def test_export_csv_service(hass: HomeAssistant, setup_integration: MockConfigEntry) -> None:
    await _make_history(hass)
    today = dt_util.now().strftime("%Y-%m-%d")
    response = await hass.services.async_call(
        DOMAIN,
        "export_csv",
        {
            "filename": "exports/test.csv",
            "start_date": today,
            "persons": ["Jean"],
            "delimiter": ";",
        },
        blocking=True,
        return_response=True,
    )
    path = response["path"]
    assert response["records"] == 1
    assert path == os.path.realpath(hass.config.path("exports/test.csv"))
    with open(path, encoding="utf-8-sig") as handle:
        lines = handle.read().splitlines()
    assert lines[0].startswith("timestamp;person;")
    assert len(lines) == 2 and "Jean" in lines[1]

    # Default name is timestamped, extension enforced.
    response = await hass.services.async_call(
        DOMAIN, "export_csv", {"filename": "sans_extension"}, blocking=True, return_response=True
    )
    assert response["path"].endswith("sans_extension.csv")
    assert response["records"] == 2
    response = await hass.services.async_call(
        DOMAIN, "export_csv", {}, blocking=True, return_response=True
    )
    assert os.path.basename(response["path"]).startswith("suivi_presence_export_")


async def test_export_csv_rejects_paths_outside_config(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN, "export_csv", {"filename": "../../etc/evil.csv"}, blocking=True
        )
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN, "export_csv", {"start_date": "not-a-date"}, blocking=True
        )
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "export_csv",
            {"start_date": "2025-02-01", "end_date": "2025-01-01"},
            blocking=True,
        )


async def test_export_excel_service(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    await _make_history(hass)
    response = await hass.services.async_call(
        DOMAIN, "export_excel", {"filename": "rapport"}, blocking=True, return_response=True
    )
    assert response["records"] == 2
    assert response["path"].endswith("rapport.xlsx")
    wb = openpyxl.load_workbook(response["path"])
    assert wb.sheetnames == ["Résumé", "Jean", "Marie"]


async def test_export_excel_without_openpyxl(
    hass: HomeAssistant, setup_integration: MockConfigEntry, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sys

    monkeypatch.setitem(sys.modules, "openpyxl", None)
    with pytest.raises(HomeAssistantError, match="openpyxl"):
        await hass.services.async_call(DOMAIN, "export_excel", {}, blocking=True)


async def test_clear_history_requires_admin(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    csv_path: str,
    hass_admin_user: MockUser,
) -> None:
    await _make_history(hass)
    user = MockUser(groups=[]).add_to_hass(hass)  # no admin group
    assert not user.is_admin
    with pytest.raises(Unauthorized):
        await hass.services.async_call(
            DOMAIN, "clear_history", {}, blocking=True, context=Context(user_id=user.id)
        )
    assert len(setup_integration.runtime_data.history) == 2

    response = await hass.services.async_call(
        DOMAIN,
        "clear_history",
        {},
        blocking=True,
        return_response=True,
        context=Context(user_id=hass_admin_user.id),
    )
    assert os.path.exists(response["backup"])
    assert setup_integration.runtime_data.history == []
    assert hass.states.get("sensor.suivi_de_presence_total_des_changements").state == "0"

    # Calls without a user (automations) are allowed.
    await _make_history_again(hass)
    await hass.services.async_call(DOMAIN, "clear_history", {}, blocking=True)
    assert setup_integration.runtime_data.history == []


async def _make_history_again(hass: HomeAssistant) -> None:
    hass.states.async_set("person.jean", "home", {"friendly_name": "Jean"})
    await hass.async_block_till_done()


async def test_services_when_not_loaded(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    assert await hass.config_entries.async_unload(setup_integration.entry_id)
    await hass.async_block_till_done()
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(DOMAIN, "export_csv", {}, blocking=True)
