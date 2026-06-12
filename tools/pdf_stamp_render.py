"""Render OHNE InDesign: Daten direkt in die exportierte Master-PDF stempeln.

Nutzt die vorhandene Master-PDF (eine Seite je Variante) als Vorlage: die
<<Platzhalter>> werden an Ort und Stelle durch die echten Werte ersetzt
(gleiche Position, Größe, Farbe). Logo/Statiktext/Layout bleiben im Original
erhalten. Voll automatisierbar mit PyMuPDF.

Hinweis: Für 100 % Schrifttreue werden die echten Helvetica-Neue-LT-Com-
Schriftdateien (Hv + Lt) benötigt – ohne sie wird ein nahe verwandter
Helvetica-Ersatz verwendet (Positionen stimmen, Laufweite minimal anders).
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

import fitz  # PyMuPDF

from app.feldmapping import auf_merge_felder, variante
from app.vcard_qr import baue_vcard, qr_png
from app.xml_import import parse_bestellung

# Variante -> Seitenindex in der Master-PDF
VARIANTE_SEITE = {"Barmag": 0, "Neumag": 1}


def _rgb(intcol: int) -> tuple[float, float, float]:
    return ((intcol >> 16) & 255) / 255, ((intcol >> 8) & 255) / 255, (intcol & 255) / 255


def _werte(felder: dict) -> dict[str, str]:
    # Namenszeile der Vorlage zeigt nur <<Vorname>> -> Vor- und Nachnamen zusammenziehen
    werte = dict(felder)
    werte["Vorname"] = (felder.get("Vorname", "") + " " + felder.get("Name", "")).strip()
    return werte


def _ersetze(text: str, werte: dict[str, str]) -> str:
    def f(m: re.Match) -> str:
        return werte.get(m.group(1).strip(), m.group(0))
    out = re.sub(r"<<([^<>]+)>>", f, text)
    return re.sub(r"\s+", " ", out).strip()


def _qr_bbox(page) -> "fitz.Rect | None":
    """Findet die QR-Bounding-Box (dichter Vektor-Cluster) in der unteren linken Ecke."""
    region = fitz.Rect(4, 80, 98, 152)
    xs: list[float] = []
    ys: list[float] = []
    for d in page.get_drawings():
        r = d["rect"]
        if r.x0 >= region.x0 - 1 and r.x1 <= region.x1 + 1 \
                and r.y0 >= region.y0 - 1 and r.y1 <= region.y1 + 1:
            xs += [r.x0, r.x1]
            ys += [r.y0, r.y1]
    if not xs:
        return None
    return fitz.Rect(min(xs), min(ys), max(xs), max(ys))


def _ersetze_qr(page, felder: dict, udx: dict) -> bool:
    """Tauscht den vCard-QR gegen einen mit den echten Personendaten aus."""
    box = _qr_bbox(page)
    if box is None:
        return False
    vcard = baue_vcard(felder, udx)
    png = Path(tempfile.mkdtemp()) / "qr.png"
    qr_png(vcard, png)
    pad = 2  # pt zusätzlicher weißer Rand (Quiet Zone)
    cover = fitz.Rect(box.x0 - pad, box.y0 - pad, box.x1 + pad, box.y1 + pad)
    page.draw_rect(cover, color=(1, 1, 1), fill=(1, 1, 1))
    page.insert_image(box, filename=str(png))
    return True


def _stempel(master_pdf, seite_idx, felder, ziel, fontfile=None, udx=None) -> Path:
    werte = _werte(felder)
    doc = fitz.open(str(master_pdf))
    page = doc[seite_idx]

    # 1) Platzhalter-Spans einsammeln
    jobs = []
    for b in page.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            for s in l["spans"]:
                if "<<" in s["text"]:
                    jobs.append({
                        "origin": fitz.Point(s["origin"]),
                        "size": s["size"],
                        "color": _rgb(s["color"]),
                        "fett": ("Hv" in s["font"]) or ("Bd" in s["font"]) or ("Bold" in s["font"]),
                        "neu": _ersetze(s["text"], werte),
                        "bbox": fitz.Rect(s["bbox"]),
                    })

    # 2) Platzhalter abdecken (weiß) und entfernen
    for j in jobs:
        page.add_redact_annot(j["bbox"], fill=(1, 1, 1))
    page.apply_redactions()

    # 3) echte Werte an gleicher Stelle setzen
    for j in jobs:
        if not j["neu"]:
            continue
        kwargs = dict(fontsize=j["size"], color=j["color"])
        if fontfile:
            kwargs["fontfile"] = fontfile
            kwargs["fontname"] = "vkfont"
        else:
            kwargs["fontname"] = "hebo" if j["fett"] else "helv"
        page.insert_text(j["origin"], j["neu"], **kwargs)

    # 4) vCard-QR mit echten Daten austauschen
    if udx is not None:
        _ersetze_qr(page, felder, udx)

    # 5) nur diese Seite behalten und speichern
    doc.select([seite_idx])
    ziel = Path(ziel)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(ziel), garbage=4, deflate=True)
    return ziel


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Daten in Master-PDF stempeln (ohne InDesign)")
    ap.add_argument("master", help="Master-PDF mit <<Platzhaltern>>")
    ap.add_argument("xml", help="Bestell-XML")
    ap.add_argument("-n", "--nummer", type=int, default=1)
    ap.add_argument("--font", default=None, help="optional: echte .ttf der Hausschrift")
    ap.add_argument("-o", "--out", default="./render_test")
    args = ap.parse_args(argv)

    bestellung = parse_bestellung(args.xml)
    karte = bestellung.karten[args.nummer - 1]
    felder = auf_merge_felder(karte.udx)
    var = variante(karte.udx)
    name = (felder["Vorname"] + "_" + felder["Name"]).replace(" ", "") or "karte"
    ziel = Path(args.out) / f"VK_{name}_{var}_gestempelt.pdf"
    _stempel(args.master, VARIANTE_SEITE.get(var, 0), felder, ziel, args.font, udx=karte.udx)
    print(f"Gestempelt (inkl. QR): {felder['Vorname']} {felder['Name']} [{var}] -> {ziel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
