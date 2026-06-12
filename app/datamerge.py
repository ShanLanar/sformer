"""Erzeugt die InDesign-Data-Merge-Datenquelle.

InDesign erwartet eine TAB-getrennte Textdatei, deren Kopfzeile exakt den
Platzhalter-Namen der Vorlage entspricht (ohne <<>>). Für zuverlässige Umlaute
schreiben wir UTF-16LE mit BOM – das liest InDesign am robustesten.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from .feldmapping import MERGE_FELDER


def _zelle(wert) -> str:
    s = "" if wert is None else str(wert)
    # Tabs/Zeilenumbrüche in Feldern würden das Format zerstören → entschärfen
    return s.replace("\t", " ").replace("\r", " ").replace("\n", " ").strip()


def schreibe_datenquelle(datensaetze: list[dict], ziel: str | Path,
                         felder: list[str] | None = None) -> Path:
    """Schreibt eine InDesign-Data-Merge-Datei (UTF-16LE, Tab-getrennt)."""
    felder = felder or MERGE_FELDER
    zeilen = ["\t".join(felder)]
    for d in datensaetze:
        zeilen.append("\t".join(_zelle(d.get(f, "")) for f in felder))
    inhalt = "\r\n".join(zeilen) + "\r\n"

    ziel = Path(ziel)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    # ﻿ -> UTF-16LE-BOM (FF FE), danach der Text in UTF-16LE
    ziel.write_bytes(("﻿" + inhalt).encode("utf-16-le"))
    return ziel


def schreibe_pro_variante(datensaetze_mit_variante: list[tuple[str, dict]],
                          ziel_ordner: str | Path) -> dict[str, Path]:
    """Gruppiert nach Variante und schreibt je eine Datenquelle.

    Erwartet eine Liste aus (variante, merge_felder_dict). Liefert
    {variante: Pfad}. Jede Variante adressiert eine eigene Master-Vorlage.
    """
    gruppen: dict[str, list[dict]] = defaultdict(list)
    for variante, daten in datensaetze_mit_variante:
        gruppen[variante].append(daten)

    ergebnis: dict[str, Path] = {}
    for variante, recs in gruppen.items():
        ziel = Path(ziel_ordner) / f"merge_{variante}.txt"
        ergebnis[variante] = schreibe_datenquelle(recs, ziel)
    return ergebnis
