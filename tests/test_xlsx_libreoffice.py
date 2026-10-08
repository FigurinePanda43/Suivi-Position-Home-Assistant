"""Open the generated workbook with a real spreadsheet application (LibreOffice).

Skipped when ``soffice`` is not installed. GitHub's ubuntu runners ship LibreOffice,
so the CI exercises it. A conversion to CSV succeeds only if LibreOffice could parse
the whole package (content types, relationships, styles, sheets).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import shutil
import subprocess
from zoneinfo import ZoneInfo

from homeassistant.util import dt as dt_util
import pytest

from custom_components.suivi_presence.export import export_to_excel
from custom_components.suivi_presence.stats import CurrentState

SOFFICE = shutil.which("soffice") or shutil.which("libreoffice")


@pytest.mark.skipif(SOFFICE is None, reason="LibreOffice not installed")
def test_libreoffice_opens_the_workbook(tmp_path: Path) -> None:
    previous = dt_util.DEFAULT_TIME_ZONE
    dt_util.set_default_time_zone(ZoneInfo("Europe/Paris"))
    try:
        history = [
            {
                "timestamp": "2025-09-01T08:30:00+02:00",
                "person": "Jean",
                "previous_zone": "home",
                "new_zone": "Travail",
                "duration_in_previous": "12:30:00",
                "duration_seconds": "45000",
                "person_entity_id": "person.jean",
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
        ]
        states = [
            CurrentState("Jean", "home", datetime(2025, 9, 1, 16, 0, tzinfo=UTC), "person.jean")
        ]
        content = export_to_excel(history, states, now=datetime(2025, 9, 2, 12, 0, tzinfo=UTC))
    finally:
        dt_util.set_default_time_zone(previous)

    source = tmp_path / "rapport.xlsx"
    source.write_bytes(content)
    profile = tmp_path / "profile"
    result = subprocess.run(
        [
            SOFFICE,
            "--headless",
            "--norestore",
            f"-env:UserInstallation=file://{profile}",
            "--convert-to",
            "csv:Text - txt - csv (StarCalc):44,34,76,1,,0,false,true,false,false,false,-1",
            "--outdir",
            str(tmp_path),
            str(source),
        ],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    # One CSV per sheet (sheet index suffix) with the -1 option; fall back to a single file.
    outputs = sorted(tmp_path.glob("rapport*.csv"))
    assert outputs, f"no CSV produced: {result.stdout} {result.stderr}"
    text = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in outputs)
    assert "Résumé" in text or "Suivi de Présence" in text
    assert "Jean" in text
    # Durations and dates were understood as numbers/dates, not text: LibreOffice
    # re-renders them (dates in its own locale order, hence both spellings).
    assert "32:30:00" in text  # 12 h 30 before 08:30 + 16:00 UTC -> noon next day
    assert "01/09/2025 08:30:00" in text or "09/01/2025 08:30:00" in text
