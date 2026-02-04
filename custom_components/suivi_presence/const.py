"""Constants for Suivi de Présence integration."""
from typing import Final

DOMAIN: Final = "suivi_presence"
VERSION: Final = "0.1.0"

# Configuration keys
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_CSV_PATH: Final = "csv_path"
CONF_TRACKED_PERSONS: Final = "tracked_persons"

# Default values
DEFAULT_SCAN_INTERVAL: Final = 30
DEFAULT_CSV_FILENAME: Final = "suivi_presence_data.csv"  # CSV brut permanent

# Services
SERVICE_EXPORT_CSV: Final = "export_csv"
SERVICE_EXPORT_EXCEL: Final = "export_excel"
SERVICE_CLEAR_HISTORY: Final = "clear_history"
SERVICE_DOWNLOAD_CSV: Final = "download_csv"

# Service parameters
ATTR_START_DATE: Final = "start_date"
ATTR_END_DATE: Final = "end_date"
ATTR_PERSONS: Final = "persons"

# Attributes
ATTR_PERSON: Final = "person"
ATTR_PREVIOUS_ZONE: Final = "previous_zone"
ATTR_NEW_ZONE: Final = "new_zone"
ATTR_TIMESTAMP: Final = "timestamp"
ATTR_DURATION: Final = "duration_in_previous"
ATTR_DURATION_SECONDS: Final = "duration_seconds"
ATTR_FILENAME: Final = "filename"

# CSV Headers
CSV_HEADERS: Final = [
    "timestamp",
    "person",
    "previous_zone",
    "new_zone",
    "duration_in_previous",
    "duration_seconds",
]

# States
STATE_HOME: Final = "home"
STATE_NOT_HOME: Final = "not_home"
STATE_UNKNOWN: Final = "unknown"

# Panel
PANEL_URL: Final = "/suivi-presence"
PANEL_TITLE: Final = "Suivi Présence"
PANEL_ICON: Final = "mdi:account-group"

# HTTP endpoints
HTTP_DOWNLOAD_PATH: Final = "/api/suivi_presence/download"
HTTP_DOWNLOAD_CSV_FILTERED: Final = "/api/suivi_presence/download/csv"
HTTP_DOWNLOAD_EXCEL: Final = "/api/suivi_presence/download/excel"
HTTP_DATA_PATH: Final = "/api/suivi_presence/data"

# Platforms
PLATFORMS: Final = ["sensor"]

# Excel sheet names
EXCEL_STATS_SECTION: Final = "Statistiques"
EXCEL_DATA_SECTION: Final = "Données"

# Statistics labels
STAT_TOTAL_TIME: Final = "Temps total"
STAT_DAILY_AVG: Final = "Moyenne journalière"
STAT_WEEKLY_AVG: Final = "Moyenne hebdomadaire"
STAT_MONTHLY_AVG: Final = "Moyenne mensuelle"
STAT_FREQUENCY: Final = "Fréquence (visites)"
STAT_FIRST_VISIT: Final = "Première visite"
STAT_LAST_VISIT: Final = "Dernière visite"
