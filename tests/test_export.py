"""Unit tests for the CSV / Excel export module."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import io
from zoneinfo import ZoneInfo

from homeassistant.util import dt as dt_util
import pytest

from custom_components.suivi_presence.const import CSV_HEADERS
from custom_components.suivi_presence.export import (
    export_to_csv,
    export_to_excel,
    filter_history,
    get_date_range_info,
)
from custom_components.suivi_presence.stats import CurrentState
from custom_components.suivi_presence.util import parse_user_datetime

PARIS = ZoneInfo("Europe/Paris")


@pytest.fixture(autouse=True)
def paris_timezone():
    previous = dt_util.DEFAULT_TIME_ZONE
    dt_util.set_default_time_zone(PARIS)
    yield
    dt_util.set_default_time_zone(previous)


@pytest.fixture
def history() -> list[dict]:
    """A mix of legacy (0.1.x, UTC, str(timedelta)) and 1.0.0 rows."""
    return [
        {
            "timestamp": "2025-09-01T06:30:00.123456+00:00",
            "person": "Jean",
            "previous_zone": "home",
            "new_zone": "Travail",
            "duration_in_previous": "12:30:00.500000",
            "duration_seconds": "45000.5",
            "person_entity_id": "",
        },
        {
            "timestamp": "2025-09-01T18:00:00+02:00",
            "person": "Jean",
            "previous_zone": "Travail",
            "new_zone": "home",
            "duration_in_previous": "9:30:00",
            "duration_seconds": "34200",
            "person_entity_id": "person.jean",
        },
        {
            "timestamp": "2025-09-02T07:00:00+02:00",
            "person": "A/B: Marie?",
            "previous_zone": "home",
            "new_zone": "not_home",
            "duration_in_previous": "",
            "duration_seconds": "",
            "person_entity_id": "person.marie",
        },
    ]


def test_filter_history_with_user_dates_does_not_crash(history: list[dict]) -> None:
    """Regression: naive user dates vs aware stored timestamps used to raise TypeError."""
    start = parse_user_datetime("2025-09-01")
    end = parse_user_datetime("2025-09-01", end_of_day=True)
    filtered = filter_history(history, start, end)
    assert [r["new_zone"] for r in filtered] == ["Travail", "home"]


def test_filter_history_by_person_name_or_entity_id(history: list[dict]) -> None:
    assert len(filter_history(history, persons=["Jean"])) == 2
    assert len(filter_history(history, persons=["person.jean"])) == 1  # legacy row has no entity id
    assert len(filter_history(history, persons=["person.marie"])) == 1


def test_export_to_csv_keeps_storage_columns(history: list[dict]) -> None:
    content = export_to_csv(history)
    lines = content.splitlines()
    assert lines[0] == ",".join(CSV_HEADERS)
    assert len(lines) == 4
    assert not content.startswith("﻿")


def test_export_to_csv_bom_and_delimiter(history: list[dict]) -> None:
    content = export_to_csv(history, delimiter=";", bom=True)
    assert content.startswith("﻿")
    assert content.splitlines()[0].lstrip("﻿") == ";".join(CSV_HEADERS)
    # Person name containing the delimiter must be quoted.
    assert '"A/B: Marie?"' not in content  # no delimiter inside, no quoting needed
    content = export_to_csv(history, delimiter="/")
    assert '"A/B: Marie?"' in content


def test_export_to_excel_builds_a_real_workbook(history: list[dict]) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    now = datetime(2025, 9, 2, 12, 0, tzinfo=UTC)
    states = [
        CurrentState("Jean", "home", datetime(2025, 9, 1, 16, 0, tzinfo=UTC), "person.jean"),
        CurrentState(
            "A/B: Marie?", "not_home", datetime(2025, 9, 2, 5, 0, tzinfo=UTC), "person.marie"
        ),
    ]
    content = export_to_excel(history, states, now=now)
    wb = openpyxl.load_workbook(io.BytesIO(content))

    # Summary first, then one sanitised sheet per person.
    assert wb.sheetnames[0] == "Résumé"
    assert "Jean" in wb.sheetnames
    assert "A_B_ Marie_" in wb.sheetnames
    assert len(wb.sheetnames) == 3

    summary = wb["Résumé"]
    headers = [c.value for c in summary[6]]
    assert headers[:4] == ["Personne", "Zone", "Temps total", "Moyenne par jour"]
    rows = list(summary.iter_rows(min_row=7, values_only=True))
    jean_home = next(r for r in rows if r[0] == "Jean" and r[1] == "home")
    # Durations are real Excel durations (openpyxl reads "[h]:mm:ss" cells back as timedelta).
    assert isinstance(jean_home[2], timedelta)
    # 12 h 30 m 0.5 s before 06:30 UTC + 16:00 UTC -> noon next day (20 h) = 32 h 30 m 0.5 s
    assert jean_home[2] == timedelta(hours=32, minutes=30, milliseconds=500)
    assert summary.cell(row=7, column=3).number_format == "[h]:mm:ss"

    jean = wb["Jean"]
    # Find the data table header and check the first data row types.
    header_row = next(
        r for r in range(1, 40) if jean.cell(row=r, column=1).value == "Date et heure"
    )
    first = jean.cell(row=header_row + 1, column=1)
    assert isinstance(first.value, datetime)
    assert first.value.tzinfo is None
    assert first.value == datetime(2025, 9, 1, 8, 30, 0)  # 06:30 UTC -> 08:30 Paris
    assert first.number_format == "dd/mm/yyyy hh:mm:ss"
    assert (
        jean.cell(row=header_row + 1, column=5).value == 45000
    )  # legacy 45000.5 -> rounded seconds
    assert jean.cell(row=header_row + 1, column=4).number_format == "[h]:mm:ss"


def test_export_to_excel_with_filters_and_duplicate_sheet_names() -> None:
    openpyxl = pytest.importorskip("openpyxl")
    long_name = "Personne avec un nom vraiment très long"
    history = [
        {
            "timestamp": "2025-09-01T10:00:00+02:00",
            "person": long_name + " A",
            "previous_zone": "home",
            "new_zone": "not_home",
            "duration_in_previous": "1:00:00",
            "duration_seconds": "3600",
            "person_entity_id": "",
        },
        {
            "timestamp": "2025-09-01T11:00:00+02:00",
            "person": long_name + " B",
            "previous_zone": "home",
            "new_zone": "not_home",
            "duration_in_previous": "1:00:00",
            "duration_seconds": "3600",
            "person_entity_id": "",
        },
    ]
    content = export_to_excel(
        history,
        [],
        start=parse_user_datetime("2025-09-01"),
        end=parse_user_datetime("2025-09-01", end_of_day=True),
        now=datetime(2025, 9, 2, tzinfo=UTC),
    )
    wb = openpyxl.load_workbook(io.BytesIO(content))
    names = wb.sheetnames
    assert len(names) == 3
    assert all(len(n) <= 31 for n in names)
    assert len(set(n.lower() for n in names)) == 3


def test_export_to_excel_empty_history() -> None:
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.load_workbook(io.BytesIO(export_to_excel([], [])))
    assert wb.sheetnames == ["Résumé"]
    assert wb["Résumé"]["A7"].value == "Aucune donnée pour cette période"


def test_xlsx_package_is_well_formed() -> None:
    """Every part of the archive is well-formed XML with the expected names."""
    import xml.etree.ElementTree as ET
    import zipfile

    history = [
        {
            "timestamp": "2025-09-01T10:00:00+02:00",
            "person": "Jean & Co <test>",
            "previous_zone": "home",
            "new_zone": "not_home",
            "duration_in_previous": "1:00:00",
            "duration_seconds": "3600",
            "person_entity_id": "person.jean",
        }
    ]
    content = export_to_excel(history, [], now=datetime(2025, 9, 2, tzinfo=UTC))
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        assert archive.testzip() is None
        names = set(archive.namelist())
        assert {
            "[Content_Types].xml",
            "_rels/.rels",
            "xl/workbook.xml",
            "xl/_rels/workbook.xml.rels",
            "xl/styles.xml",
            "xl/worksheets/sheet1.xml",
            "xl/worksheets/sheet2.xml",
        } <= names
        for name in names:
            ET.fromstring(archive.read(name))  # raises on malformed XML
        sheet2 = archive.read("xl/worksheets/sheet2.xml").decode()
        assert "Jean &amp; Co &lt;test&gt;" in sheet2
        workbook = archive.read("xl/workbook.xml").decode()
        assert 'name="Jean &amp; Co &lt;test&gt;"' in workbook
        assert "_xlnm._FilterDatabase" in workbook


def test_xlsx_writer_cells_and_sheet_options() -> None:
    from custom_components.suivi_presence.xlsx_writer import (
        STYLE_DATETIME,
        STYLE_DURATION,
        Workbook,
        column_letter,
        excel_serial,
    )

    assert column_letter(1) == "A"
    assert column_letter(26) == "Z"
    assert column_letter(27) == "AA"
    assert column_letter(703) == "AAA"
    assert excel_serial(datetime(2025, 9, 1, 12, 0)) == pytest.approx(45901.5)

    wb = Workbook()
    sheet = wb.add_sheet("It's a sheet")
    sheet.set(1, 1, "  padded  ")
    sheet.set(2, 1, datetime(2025, 9, 1, 12, 0), STYLE_DATETIME)
    sheet.set(2, 2, 0.5, STYLE_DURATION)
    sheet.set(2, 3, None)  # ignored
    sheet.set(2, 4, True)
    sheet.freeze_rows = 1
    sheet.autofilter = "A1:D2"
    sheet.set_widths((10, 20))
    openpyxl = pytest.importorskip("openpyxl")
    loaded = openpyxl.load_workbook(io.BytesIO(wb.to_bytes()))
    ws = loaded["It's a sheet"]
    assert ws["A1"].value == "  padded  "
    assert ws["A2"].value == datetime(2025, 9, 1, 12, 0)
    assert ws["A2"].number_format == "dd/mm/yyyy hh:mm:ss"
    assert ws["B2"].value == timedelta(hours=12)
    assert ws["C2"].value is None
    assert ws["D2"].value is True
    assert ws.freeze_panes == "A2"
    assert ws.auto_filter.ref == "A1:D2"
    assert ws.column_dimensions["A"].width == 10
    with pytest.raises(ValueError):
        Workbook().to_bytes()


def test_get_date_range_info(history: list[dict]) -> None:
    info = get_date_range_info(history)
    assert info["total_records"] == 3
    assert info["unique_persons"] == ["A/B: Marie?", "Jean"]
    assert info["unique_zones"] == ["Travail", "home", "not_home"]
    assert info["start_date"].startswith("2025-09-01T06:30:00")
    assert info["end_date"] == (datetime(2025, 9, 2, 5, 0, tzinfo=UTC)).isoformat()
    assert get_date_range_info([])["start_date"] is None
    assert get_date_range_info([])["total_records"] == 0
    assert timedelta(0) == timedelta(0)  # keep import used
