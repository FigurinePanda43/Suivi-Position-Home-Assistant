"""CSV and Excel exports.

The CSV export is a faithful copy of the permanent storage (same columns), with
optional filters. The Excel export is a real ``.xlsx`` workbook: a summary sheet
plus one sheet per person, with genuine date and duration cells so the file can
be sorted, filtered and summed in Excel / LibreOffice. It is written with the
standard library only (see ``xlsx_writer.py``): no package to install on the host.
"""

from __future__ import annotations

import csv
from datetime import datetime
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
from .xlsx_writer import (
    STYLE_DATETIME,
    STYLE_DATETIME_SHORT,
    STYLE_DURATION,
    STYLE_HEADER_BLUE,
    STYLE_HEADER_GREEN,
    STYLE_INT,
    STYLE_NOTE,
    STYLE_TEXT,
    STYLE_TITLE,
    Sheet,
    Workbook,
)

_LOGGER = logging.getLogger(__name__)

_INVALID_SHEET_CHARS = re.compile(r"[\[\]:*?/\\]")


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
    """Build the Excel workbook (summary + one sheet per person) and return its bytes."""
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

    stats_headers = [
        "Zone",
        "Temps total",
        "Moyenne par jour",
        "Visites",
        "Première arrivée",
        "Dernière arrivée",
        "En cours",
    ]
    data_headers = [
        "Date et heure",
        "Zone précédente",
        "Nouvelle zone",
        "Durée dans la zone précédente",
        "Durée (secondes)",
    ]

    def write_header(sheet: Sheet, row: int, headers: list[str], style: int) -> None:
        for col, text in enumerate(headers, start=1):
            sheet.set(row, col, text, style)

    def write_stats_rows(
        sheet: Sheet, row: int, zones: dict[str, ZoneStats], with_person: str | None
    ) -> int:
        for zone, stats in sorted(zones.items(), key=lambda item: -item[1].seconds):
            col = 1
            if with_person is not None:
                sheet.set(row, col, with_person, STYLE_TEXT)
                col += 1
            sheet.set(row, col, zone, STYLE_TEXT)
            sheet.set(row, col + 1, _excel_duration(stats.seconds), STYLE_DURATION)
            sheet.set(row, col + 2, _excel_duration(stats.seconds / days), STYLE_DURATION)
            sheet.set(row, col + 3, stats.visits, STYLE_INT)
            sheet.set(
                row, col + 4, local_naive(stats.first) if stats.first else "", STYLE_DATETIME_SHORT
            )
            sheet.set(
                row, col + 5, local_naive(stats.last) if stats.last else "", STYLE_DATETIME_SHORT
            )
            sheet.set(row, col + 6, "Oui" if stats.ongoing else "", STYLE_TEXT)
            row += 1
        return row

    workbook = Workbook()
    used_names: set[str] = set()

    # ---- Summary sheet ----
    sheet = workbook.add_sheet(_safe_sheet_name(EXCEL_SUMMARY_SHEET, used_names))
    sheet.set(1, 1, "Suivi de Présence — Résumé", STYLE_TITLE)
    sheet.set(2, 1, period_text)
    sheet.set(3, 1, generated_text, STYLE_NOTE)
    sheet.set(
        4,
        1,
        "Temps au format heures:minutes:secondes (les heures peuvent dépasser 24). "
        f"Moyennes calculées sur {days:.1f} jour(s).",
        STYLE_NOTE,
    )
    write_header(sheet, 6, ["Personne", *stats_headers], STYLE_HEADER_BLUE)
    row = 7
    for person in person_names:
        zones = summary.get(person)
        if zones:
            row = write_stats_rows(sheet, row, zones, person)
    if row == 7:
        sheet.set(row, 1, "Aucune donnée pour cette période")
        row += 1
    sheet.freeze_rows = 6
    sheet.autofilter = f"A6:H{max(row - 1, 6)}"
    sheet.set_widths((22, 20, 14, 16, 10, 18, 18, 10))

    # ---- One sheet per person ----
    for person in person_names:
        sheet = workbook.add_sheet(_safe_sheet_name(person, used_names))
        sheet.set(1, 1, f"{EXCEL_STATS_SECTION} — {person}", STYLE_TITLE)
        sheet.set(2, 1, period_text, STYLE_NOTE)

        write_header(sheet, 4, stats_headers, STYLE_HEADER_GREEN)
        row = 5
        zones = summary.get(person, {})
        if zones:
            row = write_stats_rows(sheet, row, zones, None)
        else:
            sheet.set(row, 1, "Aucune statistique pour cette période")
            row += 1

        data_title_row = row + 1
        sheet.set(data_title_row, 1, EXCEL_DATA_SECTION, STYLE_TITLE)
        header_row = data_title_row + 1
        write_header(sheet, header_row, data_headers, STYLE_HEADER_BLUE)
        row = header_row + 1
        for record in filtered:
            if record.get(ATTR_PERSON) != person:
                continue
            ts = parse_timestamp(record.get(ATTR_TIMESTAMP))
            if ts is not None:
                sheet.set(row, 1, local_naive(ts), STYLE_DATETIME)
            else:
                sheet.set(row, 1, record.get(ATTR_TIMESTAMP, ""), STYLE_TEXT)
            sheet.set(row, 2, record.get(ATTR_PREVIOUS_ZONE, ""), STYLE_TEXT)
            sheet.set(row, 3, record.get(ATTR_NEW_ZONE, ""), STYLE_TEXT)
            seconds = parse_duration_seconds(record)
            sheet.set(
                row, 4, _excel_duration(seconds) if seconds is not None else "", STYLE_DURATION
            )
            sheet.set(row, 5, int(round(seconds)) if seconds is not None else "", STYLE_INT)
            row += 1
        if row == header_row + 1:
            sheet.set(row, 1, "Aucun changement de zone sur la période")
            row += 1
        sheet.autofilter = f"A{header_row}:E{max(row - 1, header_row)}"
        sheet.set_widths((20, 18, 18, 26, 16, 18, 18, 10))

    return workbook.to_bytes()


__all__ = [
    "export_to_csv",
    "export_to_excel",
    "filter_history",
    "get_date_range_info",
    "get_unique_persons",
    "get_unique_zones",
]
