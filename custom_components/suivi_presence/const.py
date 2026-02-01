"""Constants for Suivi de Présence integration."""
from typing import Final

DOMAIN: Final = "suivi_presence"
VERSION: Final = "0.0.1"

# Configuration keys
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_CSV_PATH: Final = "csv_path"
CONF_TRACKED_PERSONS: Final = "tracked_persons"

# Default values
DEFAULT_SCAN_INTERVAL: Final = 30
DEFAULT_CSV_FILENAME: Final = "suivi_presence.csv"

# Services
SERVICE_EXPORT_CSV: Final = "export_csv"
SERVICE_CLEAR_HISTORY: Final = "clear_history"
SERVICE_DOWNLOAD_CSV: Final = "download_csv"

# Attributes
ATTR_PERSON: Final = "person"
ATTR_PREVIOUS_ZONE: Final = "previous_zone"
ATTR_NEW_ZONE: Final = "new_zone"
ATTR_TIMESTAMP: Final = "timestamp"
ATTR_DURATION: Final = "duration_in_previous"
ATTR_FILENAME: Final = "filename"

# CSV Headers
CSV_HEADERS: Final = [
    "timestamp",
    "person",
    "previous_zone",
    "new_zone",
    "duration_in_previous",
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
HTTP_DATA_PATH: Final = "/api/suivi_presence/data"

# Platforms
PLATFORMS: Final = ["sensor"]
