"""CSV and Excel exports.

The CSV export is a faithful copy of the permanent storage (same columns), with
optional filters. The Excel export is a real ``.xlsx`` workbook: a summary sheet
plus one sheet per person, with genuine date and duration cells so the file can
be sorted, filtered and summed in Excel / LibreOffice.

``openpyxl`` is an optional dependency: it is only needed for the Excel export
and is deliberately NOT declared in ``manifest.json`` so that a failed pip
install can never prevent the integration from loading.
"""

from __future__ import annotations

import csv
from datetime import datetime
import importlib.util
import io
import logging
import re
from typing import Any

from homeassistant.util import dt as dt_util

from .const import (
    ATTR_NEW_ZONE,
    ATTR_PERSON,
    ATTR_PREVIOUS_ZONE,
    ATTR_TIMESTAMP,
    CSV_HEADERS,
    EXCEL_DATA_SECTION,
    EXCEL_STATS_SECTION,
    EXCEL_SUMMARY_SHEET,
)
from .stats import (
    CurrentState,
    ZoneStats,
    history_date_range,
    record_person_matches,
    state_person_matches,
    zone_summary,
)
from .util import local_naive, parse_duration_seconds, parse_timestamp, period_days

_LOGGER = logging.getLogger(__name__)

OPENPYXL_PACKAGE = "openpyxl>=3.1.0"

_INVALID_SHEET_CHARS = re.compile(r"[\[\]:*?/\\]")
_EXCEL_DURATION_FORMAT = "[h]:mm:ss"
_EXCEL_DATETIME_FORMAT = "dd/mm/yyyy hh:mm:ss"
_EXCEL_DATETIME_SHORT_FORMAT = "dd/mm/yyyy hh:mm"


class ExcelExportUnavailableError(Exception):
    """Raised when the Excel export is requested but openpyxl is missing."""

    def __init__(self) -> None:
        super().__init__(
            "L'export Excel nécessite la bibliothèque openpyxl, qui n'est pas "
            "installée. Installez-la sur l'hôte Home Assistant "
            f"(pip install '{OPENPYXL_PACKAGE}') puis redémarrez Home Assistant. "
            "L'export CSV reste disponible sans openpyxl."
        )


def is_excel_available() -> bool:
    """Return True if the Excel export can be used (openpyxl importable)."""
    return importlib.util.find_spec("openpyxl") is not None


# --------------------------------------------------------------------------- #
# Filtering helpers
# --------------------------------------------------------------------------- #


def filter_history(
    history: list[dict],
    start: datetime | None = None,
    end: datetime | None = None,
    persons: set[str] | list[str] | None = None,
) -> list[dict]:
    """Filter records by (aware) date range and/or persons (names or entity ids)."""
    selection = set(persons) if persons else None
    filtered: list[dict] = []
    for record in history:
        ts = parse_timestamp(record.get(ATTR_TIMESTAMP))
        if ts is None:
            continue
        if start is not None and ts < start:
            continue
        if end is not None and ts > end:
            continue
        if not record_person_matches(record, selection):
            continue
        filtered.append(record)
    return filtered


def get_unique_persons(history: list[dict]) -> list[str]:
    """Return the sorted list of person names present in the history."""
    return sorted({r.get(ATTR_PERSON, "") for r in history if r.get(ATTR_PERSON)})


def get_unique_zones(history: list[dict]) -> list[str]:
    """Return the sorted list of zones present in the history."""
    zones: set[str] = set()
    for record in history:
        zones.add(record.get(ATTR_PREVIOUS_ZONE, "") or "")
        zones.add(record.get(ATTR_NEW_ZONE, "") or "")
    zones.discard("")
    return sorted(zones)


def get_date_range_info(history: list[dict]) -> dict[str, Any]:
    """Describe the data available in the history (for the dashboard)."""
    date_range = history_date_range(history)
    return {
        "start_date": date_range[0].isoformat() if date_range else None,
        "end_date": date_range[1].isoformat() if date_range else None,
        "total_records": len(history),
        "unique_persons": get_unique_persons(history),
        "unique_zones": get_unique_zones(history),
    }


# --------------------------------------------------------------------------- #
# CSV
# --------------------------------------------------------------------------- #


def export_to_csv(
    history: list[dict],
    start: datetime | None = None,
    end: datetime | None = None,
    persons: set[str] | list[str] | None = None,
    *,
    delimiter: str = ",",
    bom: bool = False,
) -> str:
    """Return the filtered history as CSV text (same columns as the storage file).

    ``bom`` prepends a UTF-8 byte order mark so that Microsoft Excel opens the
    file with the right encoding when double-clicked. ``delimiter`` may be ``;``
    for spreadsheets configured with a French / European locale.
    """
    filtered = filter_history(history, start, end, persons)
    output = io.StringIO()
    if bom:
        output.write("﻿")
    writer = csv.writer(output, delimiter=delimiter)
    writer.writerow(CSV_HEADERS)
    for record in filtered:
        writer.writerow([record.get(header, "") for header in CSV_HEADERS])
    return output.getvalue()


# --------------------------------------------------------------------------- #
# Excel
# --------------------------------------------------------------------------- #


def _safe_sheet_name(name: str, used: set[str]) -> str:
    """Return a valid, unique Excel sheet name (31 chars max, no forbidden chars)."""
    base = _INVALID_SHEET_CHARS.sub("_", name).strip().strip("'") or "Personne"
    base = base[:31]
    candidate = base
    index = 2
    while candidate.lower() in used:
        suffix = f" ({index})"
        candidate = f"{base[: 31 - len(suffix)]}{suffix}"
        index += 1
    used.add(candidate.lower())
    return candidate


def _excel_duration(seconds: float | None) -> float | None:
    """Convert seconds to an Excel duration (fraction of a day)."""
    if seconds is None:
        return None
    return seconds / 86400


def _period_label(start: datetime | None, end: datetime | None, history: list[dict]) -> str:
    """Human readable description of the exported period (local time)."""

    def fmt(value: datetime) -> str:
        return dt_util.as_local(value).strftime("%d/%m/%Y %H:%M")

    if start and end:
        return f"Période : du {fmt(start)} au {fmt(end)}"
    if start:
        return f"Période : depuis le {fmt(start)}"
    if end:
        return f"Période : jusqu'au {fmt(end)}"
    date_range = history_date_range(history)
    if date_range:
        return f"Période : toutes les données (du {fmt(date_range[0])} au {fmt(date_range[1])})"
    return "Période : toutes les données"


def _collect_persons(
    filtered: list[dict],
    current_states: list[CurrentState],
    selection: set[str] | None,
) -> list[str]:
    """Return the ordered list of person names that get a sheet.

    Persons come from the filtered records, from the tracked persons matching the
    selection (so a person without any transition in the period still gets a sheet
    with their ongoing stay), and from plain names given in the selection.
    """
    names: set[str] = {r[ATTR_PERSON] for r in filtered if r.get(ATTR_PERSON)}
    for state in current_states:
        if state.person and state_person_matches(state, selection):
            names.add(state.person)
    if selection:
        names.update(item for item in selection if not item.startswith("person."))
    return sorted(names, key=str.casefold)


def export_to_excel(
    history: list[dict],
    current_states: list[CurrentState] | None = None,
    *,
    start: datetime | None = None,
    end: datetime | None = None,
    persons: set[str] | list[str] | None = None,
    now: datetime | None = None,
) -> bytes:
    """Build the Excel workbook and return its bytes.

    Raises:
        ExcelExportUnavailableError: if openpyxl is not installed.
    """
    try:
        from openpyxl import Workbook  # noqa: PLC0415
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side  # noqa: PLC0415
        from openpyxl.utils import get_column_letter  # noqa: PLC0415
    except ImportError as err:
        _LOGGER.error(
            "openpyxl is not installed, Excel export unavailable. Install it with: pip install '%s'",
            OPENPYXL_PACKAGE,
        )
        raise ExcelExportUnavailableError() from err

    now = now or dt_util.utcnow()
    current_states = current_states or []
    selection = set(persons) if persons else None
    filtered = filter_history(history, start, end, selection)
    person_names = _collect_persons(filtered, current_states, selection)

    # Stays may have started before ``start``: the summary needs the full history.
    summary = zone_summary(
        history, current_states, start=start, end=end, persons=selection, now=now
    )
    date_range = history_date_range(history)
    days = period_days(start, end or now, date_range)
    period_text = _period_label(start, end, history)
    generated_text = (
        f"Généré le {dt_util.as_local(now).strftime('%d/%m/%Y à %H:%M')} par Suivi de Présence"
    )

    # Styles
    title_font = Font(bold=True, size=14)
    note_font = Font(italic=True, color="666666", size=9)
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="305496", end_color="305496", fill_type="solid")
    stats_fill = PatternFill(start_color="548235", end_color="548235", fill_type="solid")
    thin = Side(style="thin", color="BFBFBF")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)

    def write_header(ws: Any, row: int, headers: list[str], fill: Any) -> None:
        for col, text in enumerate(headers, start=1):
            cell = ws.cell(row=row, column=col, value=text)
            cell.font = header_font
            cell.fill = fill
            cell.border = border
            cell.alignment = center

    def write_stats_rows(
        ws: Any, row: int, zones: dict[str, ZoneStats], with_person: str | None
    ) -> int:
        for zone, stats in sorted(zones.items(), key=lambda item: -item[1].seconds):
            col = 1
            if with_person is not None:
                ws.cell(row=row, column=col, value=with_person).border = border
                col += 1
            ws.cell(row=row, column=col, value=zone).border = border
            cell = ws.cell(row=row, column=col + 1, value=_excel_duration(stats.seconds))
            cell.number_format = _EXCEL_DURATION_FORMAT
            cell.border = border
            cell = ws.cell(row=row, column=col + 2, value=_excel_duration(stats.seconds / days))
            cell.number_format = _EXCEL_DURATION_FORMAT
            cell.border = border
            ws.cell(row=row, column=col + 3, value=stats.visits).border = border
            for offset, value in ((4, stats.first), (5, stats.last)):
                cell = ws.cell(
                    row=row, column=col + offset, value=local_naive(value) if value else None
                )
                cell.number_format = _EXCEL_DATETIME_SHORT_FORMAT
                cell.border = border
            ws.cell(row=row, column=col + 6, value="Oui" if stats.ongoing else "").border = border
            row += 1
        return row

    stats_headers = [
        "Zone",
        "Temps total",
        "Moyenne par jour",
        "Visites",
        "Première arrivée",
        "Dernière arrivée",
        "En cours",
    ]

    wb = Workbook()
    used_names: set[str] = set()

    # ---- Summary sheet ----
    ws = wb.active
    ws.title = _safe_sheet_name(EXCEL_SUMMARY_SHEET, used_names)
    ws["A1"] = "Suivi de Présence — Résumé"
    ws["A1"].font = title_font
    ws["A2"] = period_text
    ws["A3"] = generated_text
    ws["A3"].font = note_font
    ws["A4"] = (
        "Temps au format heures:minutes:secondes (les heures peuvent dépasser 24). "
        f"Moyennes calculées sur {days:.1f} jour(s)."
    )
    ws["A4"].font = note_font
    write_header(ws, 6, ["Personne", *stats_headers], header_fill)
    row = 7
    if summary:
        for person in person_names:
            zones = summary.get(person)
            if zones:
                row = write_stats_rows(ws, row, zones, person)
    if row == 7:
        ws.cell(row=row, column=1, value="Aucune donnée pour cette période")
        row += 1
    ws.freeze_panes = "A7"
    ws.auto_filter.ref = f"A6:H{max(row - 1, 6)}"
    for col, width in enumerate((22, 20, 14, 16, 10, 18, 18, 10), start=1):
        ws.column_dimensions[get_column_letter(col)].width = width

    # ---- One sheet per person ----
    data_headers = [
        "Date et heure",
        "Zone précédente",
        "Nouvelle zone",
        "Durée dans la zone précédente",
        "Durée (secondes)",
    ]
    for person in person_names:
        ws = wb.create_sheet(title=_safe_sheet_name(person, used_names))
        ws["A1"] = f"{EXCEL_STATS_SECTION} — {person}"
        ws["A1"].font = title_font
        ws["A2"] = period_text
        ws["A2"].font = note_font

        write_header(ws, 4, stats_headers, stats_fill)
        row = 5
        zones = summary.get(person, {})
        if zones:
            row = write_stats_rows(ws, row, zones, None)
        else:
            ws.cell(row=row, column=1, value="Aucune statistique pour cette période")
            row += 1

        data_title_row = row + 1
        ws.cell(row=data_title_row, column=1, value=EXCEL_DATA_SECTION).font = title_font
        header_row = data_title_row + 1
        write_header(ws, header_row, data_headers, header_fill)
        row = header_row + 1
        for record in filtered:
            if record.get(ATTR_PERSON) != person:
                continue
            ts = parse_timestamp(record.get(ATTR_TIMESTAMP))
            cell = ws.cell(
                row=row, column=1, value=local_naive(ts) if ts else record.get(ATTR_TIMESTAMP)
            )
            cell.number_format = _EXCEL_DATETIME_FORMAT
            cell.border = border
            ws.cell(row=row, column=2, value=record.get(ATTR_PREVIOUS_ZONE, "")).border = border
            ws.cell(row=row, column=3, value=record.get(ATTR_NEW_ZONE, "")).border = border
            seconds = parse_duration_seconds(record)
            cell = ws.cell(row=row, column=4, value=_excel_duration(seconds))
            cell.number_format = _EXCEL_DURATION_FORMAT
            cell.border = border
            cell = ws.cell(
                row=row, column=5, value=int(round(seconds)) if seconds is not None else None
            )
            cell.border = border
            row += 1
        if row == header_row + 1:
            ws.cell(row=row, column=1, value="Aucun changement de zone sur la période")
            row += 1
        ws.auto_filter.ref = f"A{header_row}:E{max(row - 1, header_row)}"
        for col, width in enumerate((20, 18, 18, 26, 16, 18, 18, 10), start=1):
            ws.column_dimensions[get_column_letter(col)].width = width

    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()


__all__ = [
    "ExcelExportUnavailableError",
    "export_to_csv",
    "export_to_excel",
    "filter_history",
    "get_date_range_info",
    "get_unique_persons",
    "get_unique_zones",
    "is_excel_available",
]
