"""HTTP endpoints: downloads work, with filters, through signed paths, after reload."""

from __future__ import annotations

import io

from homeassistant.components.http.auth import async_sign_path
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.suivi_presence.const import CSV_HEADERS


async def _make_history(hass: HomeAssistant) -> None:
    hass.states.async_set("person.jean", "Travail", {"friendly_name": "Jean"})
    await hass.async_block_till_done()
    hass.states.async_set("person.marie", "home", {"friendly_name": "Marie"})
    await hass.async_block_till_done()


async def test_full_csv_download(
    hass: HomeAssistant, setup_integration: MockConfigEntry, hass_client: ClientSessionGenerator
) -> None:
    """Regression: used to fail with 500 (charset in content_type)."""
    await _make_history(hass)
    client = await hass_client()
    resp = await client.get("/api/suivi_presence/download")
    assert resp.status == 200
    assert resp.headers["Content-Type"] == "text/csv; charset=utf-8"
    assert resp.headers["Content-Disposition"].startswith(
        'attachment; filename="suivi_presence_complet_'
    )
    raw = await resp.read()
    assert raw.startswith("﻿".encode())  # BOM for Excel
    text = raw.decode("utf-8-sig")
    lines = text.splitlines()
    assert lines[0] == ",".join(CSV_HEADERS)
    assert len(lines) == 3
    assert "Jean" in lines[1] and "Marie" in lines[2]


async def test_filtered_csv_download_with_dates_and_persons(
    hass: HomeAssistant, setup_integration: MockConfigEntry, hass_client: ClientSessionGenerator
) -> None:
    """Regression: date filters used to raise TypeError (naive vs aware)."""
    await _make_history(hass)
    client = await hass_client()
    today = dt_util.now().strftime("%Y-%m-%d")

    resp = await client.get(f"/api/suivi_presence/download/csv?start_date={today}&end_date={today}")
    assert resp.status == 200
    lines = (await resp.text()).lstrip("﻿").splitlines()
    assert len(lines) == 3

    resp = await client.get(f"/api/suivi_presence/download/csv?start_date={today}&persons=Marie")
    assert resp.status == 200
    lines = (await resp.text()).lstrip("﻿").splitlines()
    assert len(lines) == 2 and "Marie" in lines[1]

    resp = await client.get("/api/suivi_presence/download/csv?persons=person.jean&delimiter=%3B")
    assert resp.status == 200
    lines = (await resp.text()).lstrip("﻿").splitlines()
    assert lines[0] == ";".join(CSV_HEADERS)
    assert len(lines) == 2 and "Jean" in lines[1]

    # A period in the far past returns only the header.
    resp = await client.get(
        "/api/suivi_presence/download/csv?start_date=2000-01-01&end_date=2000-01-02"
    )
    assert resp.status == 200
    assert len((await resp.text()).lstrip("﻿").splitlines()) == 1

    # ISO datetimes without offset are accepted (local time).
    resp = await client.get("/api/suivi_presence/download/csv?start_date=2000-01-01T00:00:00")
    assert resp.status == 200


async def test_invalid_query_parameters(
    hass: HomeAssistant, setup_integration: MockConfigEntry, hass_client: ClientSessionGenerator
) -> None:
    client = await hass_client()
    resp = await client.get("/api/suivi_presence/download/csv?start_date=31/12/2025")
    assert resp.status == 400
    assert "error" in await resp.json()
    resp = await client.get(
        "/api/suivi_presence/download/csv?start_date=2025-02-01&end_date=2025-01-01"
    )
    assert resp.status == 400
    resp = await client.get("/api/suivi_presence/download/csv?delimiter=%7C")
    assert resp.status == 400
    resp = await client.get("/api/suivi_presence/download/excel?start_date=bad")
    assert resp.status == 400


async def test_excel_download_is_a_real_workbook(
    hass: HomeAssistant, setup_integration: MockConfigEntry, hass_client: ClientSessionGenerator
) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    await _make_history(hass)
    client = await hass_client()
    today = dt_util.now().strftime("%Y-%m-%d")
    resp = await client.get(
        f"/api/suivi_presence/download/excel?start_date={today}&persons=Jean,Marie"
    )
    assert resp.status == 200
    assert resp.headers["Content-Type"] == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert resp.headers["Content-Disposition"].endswith('.xlsx"')
    content = await resp.read()
    assert content[:2] == b"PK"  # zip container of an .xlsx
    wb = openpyxl.load_workbook(io.BytesIO(content))
    assert wb.sheetnames == ["Résumé", "Jean", "Marie"]
    summary = wb["Résumé"]
    persons_in_summary = {
        row[0] for row in summary.iter_rows(min_row=7, values_only=True) if row[0]
    }
    assert persons_in_summary == {"Jean", "Marie"}


async def test_data_endpoint(
    hass: HomeAssistant, setup_integration: MockConfigEntry, hass_client: ClientSessionGenerator
) -> None:
    await _make_history(hass)
    client = await hass_client()
    resp = await client.get("/api/suivi_presence/data?limit=1")
    assert resp.status == 200
    assert resp.headers["Content-Type"] == "application/json; charset=utf-8"
    data = await resp.json()
    assert data["tracking"] is True
    assert {p["name"] for p in data["persons"]} == {"Jean", "Marie"}
    assert data["total_records"] == 2
    assert data["history"]["total"] == 2
    assert len(data["history"]["records"]) == 1
    assert data["history"]["truncated"] is True
    assert data["history"]["records"][0]["person"] == "Marie"  # newest first
    assert "summary" in data["history"]
    assert data["data_range"]["total_records"] == 2


async def test_endpoints_require_authentication(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    hass_client_no_auth: ClientSessionGenerator,
) -> None:
    client = await hass_client_no_auth()
    for path in (
        "/api/suivi_presence/download",
        "/api/suivi_presence/download/csv",
        "/api/suivi_presence/download/excel",
        "/api/suivi_presence/data",
    ):
        resp = await client.get(path)
        assert resp.status == 401, path


async def test_signed_path_download_without_token(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    hass_client_no_auth: ClientSessionGenerator,
    hass_admin_user,
) -> None:
    """The card downloads through auth/sign_path: the signed URL alone must work."""
    await _make_history(hass)
    refresh_token = await hass.auth.async_create_refresh_token(
        hass_admin_user, "https://example.com"
    )
    today = dt_util.now().strftime("%Y-%m-%d")
    path = f"/api/suivi_presence/download/csv?start_date={today}"
    signed = async_sign_path(
        hass, path, dt_util.dt.timedelta(seconds=120), refresh_token_id=refresh_token.id
    )
    client = await hass_client_no_auth()
    resp = await client.get(signed)
    assert resp.status == 200
    assert len((await resp.text()).lstrip("﻿").splitlines()) == 3


async def test_endpoints_follow_reload(
    hass: HomeAssistant, setup_integration: MockConfigEntry, hass_client: ClientSessionGenerator
) -> None:
    """Regression: views used to keep a reference to the tracker of the first setup."""
    await _make_history(hass)
    assert await hass.config_entries.async_reload(setup_integration.entry_id)
    await hass.async_block_till_done()
    hass.states.async_set("person.jean", "home", {"friendly_name": "Jean"})
    await hass.async_block_till_done()
    client = await hass_client()
    resp = await client.get("/api/suivi_presence/download")
    assert resp.status == 200
    assert len((await resp.text()).lstrip("﻿").splitlines()) == 4  # 3 records after reload


async def test_endpoints_when_integration_not_loaded(
    hass: HomeAssistant, setup_integration: MockConfigEntry, hass_client: ClientSessionGenerator
) -> None:
    assert await hass.config_entries.async_unload(setup_integration.entry_id)
    await hass.async_block_till_done()
    client = await hass_client()
    resp = await client.get("/api/suivi_presence/download")
    assert resp.status == 503
    assert "error" in await resp.json()


async def test_card_is_served_and_registered_as_frontend_resource(
    hass: HomeAssistant, setup_integration: MockConfigEntry, hass_client: ClientSessionGenerator
) -> None:
    from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL

    manager = hass.data[DATA_EXTRA_MODULE_URL]
    urls = list(getattr(manager, "urls", manager))
    assert any(u.startswith("/suivi_presence/suivi-presence-card.js?v=") for u in urls)
    client = await hass_client()
    for path in (
        "/suivi_presence/suivi-presence-card.js",
        "/local/suivi_presence/suivi-presence-card.js",
    ):
        resp = await client.get(path)
        assert resp.status == 200, path
        assert "customElements.define" in await resp.text()
