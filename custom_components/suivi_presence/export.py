"""
Export module for Suivi de Présence.

Handles CSV and Excel exports with filtering and statistics.
"""
from __future__ import annotations

import csv
import io
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from .const import (
    ATTR_DURATION,
    ATTR_DURATION_SECONDS,
    ATTR_NEW_ZONE,
    ATTR_PERSON,
    ATTR_PREVIOUS_ZONE,
    ATTR_TIMESTAMP,
    CSV_HEADERS,
    EXCEL_DATA_SECTION,
    EXCEL_STATS_SECTION,
    STAT_DAILY_AVG,
    STAT_FIRST_VISIT,
    STAT_FREQUENCY,
    STAT_LAST_VISIT,
    STAT_MONTHLY_AVG,
    STAT_TOTAL_TIME,
    STAT_WEEKLY_AVG,
)

_LOGGER = logging.getLogger(__name__)


def parse_duration(duration_str: str) -> timedelta | None:
    """Parse a duration string to timedelta."""
    if not duration_str:
        return None

    try:
        # Format: "H:MM:SS" or "D days, H:MM:SS"
        if "day" in duration_str:
            parts = duration_str.split(", ")
            days = int(parts[0].split()[0])
            time_parts = parts[1].split(":")
        else:
            days = 0
            time_parts = duration_str.split(":")

        hours = int(time_parts[0])
        minutes = int(time_parts[1])
        seconds = float(time_parts[2]) if len(time_parts) > 2 else 0

        return timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
    except (ValueError, IndexError):
        return None


def format_duration(td: timedelta | None) -> str:
    """Format a timedelta to human-readable string."""
    if td is None:
        return "N/A"

    total_seconds = int(td.total_seconds())
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    if days > 0:
        return f"{days}j {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"


def filter_history(
    history: list[dict],
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    persons: list[str] | None = None,
) -> list[dict]:
    """Filter history by date range and/or persons."""
    filtered = []

    for record in history:
        # Parse timestamp
        timestamp_str = record.get(ATTR_TIMESTAMP, "")
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
        except (ValueError, TypeError):
            continue

        # Filter by date range
        if start_date and timestamp < start_date:
            continue
        if end_date and timestamp > end_date:
            continue

        # Filter by persons
        if persons:
            person = record.get(ATTR_PERSON, "")
            if person not in persons:
                continue

        filtered.append(record)

    return filtered


def get_unique_persons(history: list[dict]) -> list[str]:
    """Get list of unique persons from history."""
    persons = set()
    for record in history:
        person = record.get(ATTR_PERSON, "")
        if person:
            persons.add(person)
    return sorted(list(persons))


def get_unique_zones(history: list[dict]) -> list[str]:
    """Get list of unique zones from history."""
    zones = set()
    for record in history:
        zones.add(record.get(ATTR_PREVIOUS_ZONE, ""))
        zones.add(record.get(ATTR_NEW_ZONE, ""))
    zones.discard("")
    return sorted(list(zones))


def calculate_zone_statistics(
    history: list[dict],
    person: str | None = None,
) -> dict[str, dict[str, Any]]:
    """
    Calculate statistics for time spent in each zone.

    Returns:
        Dict with zone names as keys and statistics as values.
    """
    # Filter by person if specified
    if person:
        history = [r for r in history if r.get(ATTR_PERSON) == person]

    if not history:
        return {}

    # Group by zone (new_zone = where the person arrived)
    zone_stats: dict[str, dict] = defaultdict(
        lambda: {
            "total_seconds": 0,
            "visits": 0,
            "first_visit": None,
            "last_visit": None,
            "durations": [],
        }
    )

    for record in history:
        zone = record.get(ATTR_NEW_ZONE, "")
        if not zone:
            continue

        timestamp_str = record.get(ATTR_TIMESTAMP, "")
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
        except (ValueError, TypeError):
            timestamp = None

        # Count visit
        zone_stats[zone]["visits"] += 1

        # Track first and last visit
        if timestamp:
            if (
                zone_stats[zone]["first_visit"] is None
                or timestamp < zone_stats[zone]["first_visit"]
            ):
                zone_stats[zone]["first_visit"] = timestamp
            if (
                zone_stats[zone]["last_visit"] is None
                or timestamp > zone_stats[zone]["last_visit"]
            ):
                zone_stats[zone]["last_visit"] = timestamp

        # Add duration (duration is time spent in PREVIOUS zone before arriving here)
        # We need to look at the next record to get duration IN this zone
        duration_str = record.get(ATTR_DURATION, "")
        duration_seconds = record.get(ATTR_DURATION_SECONDS)

        if duration_seconds:
            try:
                zone_stats[record.get(ATTR_PREVIOUS_ZONE, "")]["total_seconds"] += float(
                    duration_seconds
                )
            except (ValueError, TypeError):
                pass
        elif duration_str:
            duration = parse_duration(duration_str)
            if duration:
                prev_zone = record.get(ATTR_PREVIOUS_ZONE, "")
                if prev_zone:
                    zone_stats[prev_zone]["total_seconds"] += duration.total_seconds()

    # Calculate date range for averages
    all_timestamps = []
    for record in history:
        try:
            ts = datetime.fromisoformat(record.get(ATTR_TIMESTAMP, ""))
            all_timestamps.append(ts)
        except (ValueError, TypeError):
            pass

    if all_timestamps:
        min_date = min(all_timestamps)
        max_date = max(all_timestamps)
        total_days = max((max_date - min_date).days, 1)
        total_weeks = max(total_days / 7, 1)
        total_months = max(total_days / 30, 1)
    else:
        total_days = 1
        total_weeks = 1
        total_months = 1

    # Build final statistics
    result = {}
    for zone, stats in zone_stats.items():
        total_seconds = stats["total_seconds"]
        total_time = timedelta(seconds=total_seconds)

        result[zone] = {
            STAT_TOTAL_TIME: format_duration(total_time),
            "total_seconds": total_seconds,
            STAT_DAILY_AVG: format_duration(
                timedelta(seconds=total_seconds / total_days) if total_days else None
            ),
            STAT_WEEKLY_AVG: format_duration(
                timedelta(seconds=total_seconds / total_weeks) if total_weeks else None
            ),
            STAT_MONTHLY_AVG: format_duration(
                timedelta(seconds=total_seconds / total_months) if total_months else None
            ),
            STAT_FREQUENCY: stats["visits"],
            STAT_FIRST_VISIT: (
                stats["first_visit"].strftime("%Y-%m-%d %H:%M")
                if stats["first_visit"]
                else "N/A"
            ),
            STAT_LAST_VISIT: (
                stats["last_visit"].strftime("%Y-%m-%d %H:%M")
                if stats["last_visit"]
                else "N/A"
            ),
        }

    return result


def export_to_csv(
    history: list[dict],
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    persons: list[str] | None = None,
) -> str:
    """
    Export filtered history to CSV string.

    Args:
        history: Full history list
        start_date: Optional start date filter
        end_date: Optional end date filter
        persons: Optional list of persons to include

    Returns:
        CSV content as string
    """
    filtered = filter_history(history, start_date, end_date, persons)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(CSV_HEADERS)

    for record in filtered:
        writer.writerow(
            [
                record.get(ATTR_TIMESTAMP, ""),
                record.get(ATTR_PERSON, ""),
                record.get(ATTR_PREVIOUS_ZONE, ""),
                record.get(ATTR_NEW_ZONE, ""),
                record.get(ATTR_DURATION, ""),
                record.get(ATTR_DURATION_SECONDS, ""),
            ]
        )

    return output.getvalue()


def export_to_excel(
    history: list[dict],
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    persons: list[str] | None = None,
) -> bytes:
    """
    Export filtered history to Excel with one sheet per person and statistics.

    Args:
        history: Full history list
        start_date: Optional start date filter
        end_date: Optional end date filter
        persons: Optional list of persons to include

    Returns:
        Excel file content as bytes
    """
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
        from openpyxl.utils import get_column_letter
        from openpyxl.utils.dataframe import dataframe_to_rows
    except ImportError:
        _LOGGER.error("openpyxl is not installed. Please install it to use Excel export.")
        raise

    # Filter history
    filtered = filter_history(history, start_date, end_date, persons)

    # Get unique persons (either from filter or from data)
    if persons:
        unique_persons = persons
    else:
        unique_persons = get_unique_persons(filtered)

    if not unique_persons:
        unique_persons = ["Aucune donnée"]

    # Create workbook
    wb = Workbook()
    wb.remove(wb.active)  # Remove default sheet

    # Styles
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    stat_header_fill = PatternFill(
        start_color="70AD47", end_color="70AD47", fill_type="solid"
    )
    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )
    center_alignment = Alignment(horizontal="center", vertical="center")

    # Create a sheet for each person
    for person in unique_persons:
        # Create sheet with safe name (Excel limits to 31 chars)
        sheet_name = person[:31] if len(person) > 31 else person
        ws = wb.create_sheet(title=sheet_name)

        # Get person's data
        person_history = [r for r in filtered if r.get(ATTR_PERSON) == person]

        # === STATISTICS SECTION ===
        ws["A1"] = f"📊 {EXCEL_STATS_SECTION} - {person}"
        ws["A1"].font = Font(bold=True, size=14)
        ws.merge_cells("A1:G1")

        # Calculate statistics for this person
        stats = calculate_zone_statistics(filtered, person)

        if stats:
            # Statistics headers
            stat_headers = [
                "Zone",
                STAT_TOTAL_TIME,
                STAT_DAILY_AVG,
                STAT_WEEKLY_AVG,
                STAT_MONTHLY_AVG,
                STAT_FREQUENCY,
                STAT_FIRST_VISIT,
                STAT_LAST_VISIT,
            ]

            row = 3
            for col, header in enumerate(stat_headers, 1):
                cell = ws.cell(row=row, column=col, value=header)
                cell.font = header_font
                cell.fill = stat_header_fill
                cell.border = thin_border
                cell.alignment = center_alignment

            # Statistics data
            row = 4
            for zone, zone_stats in sorted(stats.items()):
                ws.cell(row=row, column=1, value=zone).border = thin_border
                ws.cell(
                    row=row, column=2, value=zone_stats.get(STAT_TOTAL_TIME, "N/A")
                ).border = thin_border
                ws.cell(
                    row=row, column=3, value=zone_stats.get(STAT_DAILY_AVG, "N/A")
                ).border = thin_border
                ws.cell(
                    row=row, column=4, value=zone_stats.get(STAT_WEEKLY_AVG, "N/A")
                ).border = thin_border
                ws.cell(
                    row=row, column=5, value=zone_stats.get(STAT_MONTHLY_AVG, "N/A")
                ).border = thin_border
                ws.cell(
                    row=row, column=6, value=zone_stats.get(STAT_FREQUENCY, 0)
                ).border = thin_border
                ws.cell(
                    row=row, column=7, value=zone_stats.get(STAT_FIRST_VISIT, "N/A")
                ).border = thin_border
                ws.cell(
                    row=row, column=8, value=zone_stats.get(STAT_LAST_VISIT, "N/A")
                ).border = thin_border
                row += 1

            stats_end_row = row
        else:
            ws["A3"] = "Aucune statistique disponible"
            stats_end_row = 4

        # === DATA SECTION ===
        data_start_row = stats_end_row + 2

        ws.cell(row=data_start_row, column=1, value=f"📋 {EXCEL_DATA_SECTION}")
        ws.cell(row=data_start_row, column=1).font = Font(bold=True, size=14)
        ws.merge_cells(f"A{data_start_row}:F{data_start_row}")

        # Data headers
        data_headers = [
            "Date/Heure",
            "Zone précédente",
            "Nouvelle zone",
            "Durée (zone préc.)",
            "Durée (secondes)",
        ]

        header_row = data_start_row + 2
        for col, header in enumerate(data_headers, 1):
            cell = ws.cell(row=header_row, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = thin_border
            cell.alignment = center_alignment

        # Data rows
        row = header_row + 1
        for record in person_history:
            timestamp_str = record.get(ATTR_TIMESTAMP, "")
            try:
                timestamp = datetime.fromisoformat(timestamp_str)
                formatted_ts = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                formatted_ts = timestamp_str

            ws.cell(row=row, column=1, value=formatted_ts).border = thin_border
            ws.cell(
                row=row, column=2, value=record.get(ATTR_PREVIOUS_ZONE, "")
            ).border = thin_border
            ws.cell(
                row=row, column=3, value=record.get(ATTR_NEW_ZONE, "")
            ).border = thin_border
            ws.cell(
                row=row, column=4, value=record.get(ATTR_DURATION, "")
            ).border = thin_border
            ws.cell(
                row=row, column=5, value=record.get(ATTR_DURATION_SECONDS, "")
            ).border = thin_border
            row += 1

        # Auto-adjust column widths
        for col in range(1, 9):
            ws.column_dimensions[get_column_letter(col)].width = 18

    # Save to bytes
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return output.getvalue()


def get_date_range_info(history: list[dict]) -> dict:
    """Get information about the date range in history."""
    if not history:
        return {
            "start_date": None,
            "end_date": None,
            "total_records": 0,
            "unique_persons": [],
            "unique_zones": [],
        }

    timestamps = []
    for record in history:
        try:
            ts = datetime.fromisoformat(record.get(ATTR_TIMESTAMP, ""))
            timestamps.append(ts)
        except (ValueError, TypeError):
            pass

    return {
        "start_date": min(timestamps).isoformat() if timestamps else None,
        "end_date": max(timestamps).isoformat() if timestamps else None,
        "total_records": len(history),
        "unique_persons": get_unique_persons(history),
        "unique_zones": get_unique_zones(history),
    }
