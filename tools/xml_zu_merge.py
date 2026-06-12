"""CLI: openTRANS-Bestell-XML → InDesign-Data-Merge-Datenquelle(n).

Beispiel:
    python -m tools.xml_zu_merge bestellung.xml -o ./ausgabe

Schreibt je Variante eine Datei merge_<Variante>.txt und gibt eine
Übersichtstabelle der gemappten Felder aus.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from app.datamerge import schreibe_pro_variante
from app.feldmapping import MERGE_FELDER, auf_merge_felder, variante
from app.xml_import import parse_bestellung


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Bestell-XML in InDesign-Merge-Daten umwandeln")
    ap.add_argument("xml", help="Pfad zur openTRANS-Bestell-XML")
    ap.add_argument("-o", "--out", default="./ausgabe", help="Zielordner (Standard: ./ausgabe)")
    args = ap.parse_args(argv)

    bestellung = parse_bestellung(args.xml)
    print(f"Bestellung {bestellung.order_id} · {len(bestellung.karten)} Karte(n)")
    print(f"Proof-/Freigabe-Empfänger: {bestellung.besteller.anzeigename} <{bestellung.besteller.email}>\n")

    datensaetze: list[tuple[str, dict]] = []
    for k in bestellung.karten:
        felder = auf_merge_felder(k.udx)
        var = variante(k.udx)
        datensaetze.append((var, felder))
        print(f"— Karte {k.line_id} [{var}] " + "-" * 30)
        for f in MERGE_FELDER:
            wert = felder.get(f, "")
            print(f"    {f:<20} {wert}")
        print()

    pfade = schreibe_pro_variante(datensaetze, args.out)
    print("Geschriebene Datenquellen:")
    for var, pfad in pfade.items():
        print(f"    {var}: {pfad}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
