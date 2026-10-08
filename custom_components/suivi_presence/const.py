"""Constants for the Suivi de Présence integration."""

from __future__ import annotations

from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "suivi_presence"

# --- Configuration (config entry data / options) -----------------------------
CONF_CSV_PATH: Final = "csv_path"
CONF_TRACKED_PERSONS: Final = "tracked_persons"

DEFAULT_CSV_FILENAME: Final = "suivi_presence_data.csv"

# --- Services -----------------------------------------------------------------
SERVICE_EXPORT_CSV: Final = "export_csv"
SERVICE_EXPORT_EXCEL: Final = "export_excel"
SERVICE_CLEAR_HISTORY: Final = "clear_history"

ATTR_FILENAME: Final = "filename"
ATTR_START_DATE: Final = "start_date"
ATTR_END_DATE: Final = "end_date"
ATTR_PERSONS: Final = "persons"
ATTR_DELIMITER: Final = "delimiter"

# --- CSV columns (permanent storage) ------------------------------------------
# Rule: columns are only ever ADDED, never renamed or removed (see context.md).
ATTR_TIMESTAMP: Final = "timestamp"
ATTR_PERSON: Final = "person"
ATTR_PREVIOUS_ZONE: Final = "previous_zone"
ATTR_NEW_ZONE: Final = "new_zone"
ATTR_DURATION: Final = "duration_in_previous"
ATTR_DURATION_SECONDS: Final = "duration_seconds"
ATTR_PERSON_ENTITY_ID: Final = "person_entity_id"  # added in 1.0.0

CSV_HEADERS: Final[list[str]] = [
    ATTR_TIMESTAMP,
    ATTR_PERSON,
    ATTR_PREVIOUS_ZONE,
    ATTR_NEW_ZONE,
    ATTR_DURATION,
    ATTR_DURATION_SECONDS,
    ATTR_PERSON_ENTITY_ID,
]

# Header of the files written by versions <= 0.1.1 (used to detect migration).
LEGACY_CSV_HEADERS_0_1: Final[list[str]] = CSV_HEADERS[:6]
LEGACY_CSV_HEADERS_0_0: Final[list[str]] = CSV_HEADERS[:5]

# --- HTTP endpoints -------------------------------------------------------------
HTTP_DOWNLOAD_PATH: Final = "/api/suivi_presence/download"
HTTP_DOWNLOAD_CSV_FILTERED: Final = "/api/suivi_presence/download/csv"
HTTP_DOWNLOAD_EXCEL: Final = "/api/suivi_presence/download/excel"
HTTP_DATA_PATH: Final = "/api/suivi_presence/data"

# Static files (Lovelace card). Served from custom_components/suivi_presence/www.
STATIC_URL_BASE: Final = "/suivi_presence"
CARD_FILENAME: Final = "suivi-presence-card.js"

# --- WebSocket commands ---------------------------------------------------------
WS_OVERVIEW: Final = "suivi_presence/overview"
WS_HISTORY: Final = "suivi_presence/history"

# --- Platforms ------------------------------------------------------------------
PLATFORMS: Final[list[Platform]] = [Platform.SENSOR]

# --- Export limits ----------------------------------------------------------------
MAX_HISTORY_RESULTS: Final = 2000  # websocket history page size (records)
CSV_DELIMITERS: Final[tuple[str, ...]] = (",", ";")

# --- Excel labels (French, the integration's primary language) -------------------
EXCEL_SUMMARY_SHEET: Final = "Résumé"
EXCEL_STATS_SECTION: Final = "Statistiques par zone"
EXCEL_DATA_SECTION: Final = "Changements de zone"
