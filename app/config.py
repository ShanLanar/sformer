"""Zentrale Konfiguration.

Die Einstellungen werden aus Umgebungsvariablen gelesen. Optional wird eine
``.env``-Datei im Projektwurzelverzeichnis eingelesen (ohne Zusatzbibliothek).
So lässt sich das Tool ohne Setup starten – fehlende Werte haben sinnvolle
Standardwerte, und ohne SMTP-Zugang landen E-Mails in einer lokalen Outbox.
"""

from __future__ import annotations

import os
from pathlib import Path

BASIS_VERZEICHNIS = Path(__file__).resolve().parent.parent


def _lade_dotenv(pfad: Path) -> None:
    """Minimaler .env-Loader (KEY=VALUE pro Zeile, # als Kommentar)."""
    if not pfad.exists():
        return
    for zeile in pfad.read_text(encoding="utf-8").splitlines():
        zeile = zeile.strip()
        if not zeile or zeile.startswith("#") or "=" not in zeile:
            continue
        schluessel, _, wert = zeile.partition("=")
        schluessel = schluessel.strip()
        wert = wert.strip().strip('"').strip("'")
        # Bereits gesetzte echte Umgebungsvariablen haben Vorrang.
        os.environ.setdefault(schluessel, wert)


_lade_dotenv(BASIS_VERZEICHNIS / ".env")


def _bool(name: str, standard: bool) -> bool:
    wert = os.environ.get(name)
    if wert is None:
        return standard
    return wert.strip().lower() in {"1", "true", "yes", "ja", "on"}


class Einstellungen:
    """Anwendungs-Einstellungen, gebündelt an einer Stelle."""

    # Anzeige / Branding
    APP_NAME: str = os.environ.get("APP_NAME", "ABE Druckvorstufe")
    FIRMA: str = os.environ.get("FIRMA", "ABE GmbH")
    FARBE_AKZENT: str = os.environ.get("FARBE_AKZENT", "#E8930A")  # ABE-Orange
    FARBE_DUNKEL: str = os.environ.get("FARBE_DUNKEL", "#2D2D2D")  # Anthrazit

    # Basis-URL für die Links in der Freigabe-Mail (von außen erreichbar!)
    BASE_URL: str = os.environ.get("BASE_URL", "http://localhost:8000").rstrip("/")

    # Speicherorte
    DATA_DIR: Path = Path(os.environ.get("DATA_DIR", str(BASIS_VERZEICHNIS / "data")))
    OUTBOX_DIR: Path = Path(os.environ.get("OUTBOX_DIR", str(BASIS_VERZEICHNIS / "outbox")))

    @property
    def DB_PFAD(self) -> Path:
        return self.DATA_DIR / "auftraege.db"

    @property
    def UPLOAD_DIR(self) -> Path:
        return self.DATA_DIR / "uploads"

    # Freigabe
    FREIGABE_GUELTIGKEIT_TAGE: int = int(os.environ.get("FREIGABE_GUELTIGKEIT_TAGE", "7"))

    # E-Mail / SMTP. Ohne SMTP_ENABLED=true werden Mails in die Outbox geschrieben.
    SMTP_ENABLED: bool = _bool("SMTP_ENABLED", False)
    SMTP_HOST: str = os.environ.get("SMTP_HOST", "")
    SMTP_PORT: int = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USER: str = os.environ.get("SMTP_USER", "")
    SMTP_PASSWORD: str = os.environ.get("SMTP_PASSWORD", "")
    SMTP_USE_TLS: bool = _bool("SMTP_USE_TLS", True)
    SMTP_FROM: str = os.environ.get("SMTP_FROM", "vorstufe@example.com")
    SMTP_FROM_NAME: str = os.environ.get("SMTP_FROM_NAME", "ABE Druckvorstufe")
    # Interne Benachrichtigung an die Kollegin, sobald der Kunde entscheidet.
    BENACHRICHTIGUNG_AN: str = os.environ.get("BENACHRICHTIGUNG_AN", "")

    def verzeichnisse_anlegen(self) -> None:
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.OUTBOX_DIR.mkdir(parents=True, exist_ok=True)


einstellungen = Einstellungen()
