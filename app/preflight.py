"""Preflight-Basisprüfung für hochgeladene PDFs.

Bewusst schlank gehalten: liest Seitenzahl und Seitenmaße und gibt einfache
Hinweise zurück. pypdf wird verzögert importiert, damit die Anwendung auch
dann startet, wenn die Bibliothek (noch) nicht verfügbar ist.
"""

from __future__ import annotations

from pathlib import Path

# 1 PostScript-Punkt = 1/72 Zoll = 25.4/72 mm
PT_ZU_MM = 25.4 / 72.0


def pruefe_pdf(pfad: str | Path) -> dict:
    """Liefert ein Ergebnis-Dict mit Eckdaten und Hinweisen.

    Schlägt nie hart fehl – im Fehlerfall steht der Grund in ``fehler``.
    """
    ergebnis: dict = {
        "ok": False,
        "seitenanzahl": None,
        "breite_mm": None,
        "hoehe_mm": None,
        "verschluesselt": False,
        "hinweise": [],
        "fehler": None,
    }

    pfad = Path(pfad)
    if not pfad.exists():
        ergebnis["fehler"] = "Datei nicht gefunden."
        return ergebnis

    try:
        from pypdf import PdfReader
    except Exception as exc:  # pragma: no cover - umgebungsabhängig
        ergebnis["fehler"] = f"pypdf nicht verfügbar: {exc}"
        return ergebnis

    try:
        reader = PdfReader(str(pfad))
        ergebnis["verschluesselt"] = reader.is_encrypted
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                ergebnis["hinweise"].append("PDF ist verschlüsselt – Prüfung eingeschränkt.")

        ergebnis["seitenanzahl"] = len(reader.pages)

        seite = reader.pages[0]
        box = seite.mediabox
        breite = round(float(box.width) * PT_ZU_MM, 1)
        hoehe = round(float(box.height) * PT_ZU_MM, 1)
        ergebnis["breite_mm"] = breite
        ergebnis["hoehe_mm"] = hoehe

        if breite < 10 or hoehe < 10:
            ergebnis["hinweise"].append("Seitenformat wirkt ungewöhnlich klein.")
        ergebnis["ok"] = True
    except Exception as exc:
        ergebnis["fehler"] = f"PDF konnte nicht gelesen werden: {exc}"

    return ergebnis


def kurzfassung(ergebnis: dict) -> str:
    """Einzeiler für die Oberfläche."""
    if ergebnis.get("fehler"):
        return f"Preflight: {ergebnis['fehler']}"
    if not ergebnis.get("ok"):
        return "Preflight: keine Daten."
    teile = [f"{ergebnis['seitenanzahl']} Seite(n)"]
    if ergebnis.get("breite_mm") and ergebnis.get("hoehe_mm"):
        teile.append(f"{ergebnis['breite_mm']} × {ergebnis['hoehe_mm']} mm")
    return "Preflight: " + ", ".join(teile)
