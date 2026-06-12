"""Vorschau-/Test-Renderer für Visitenkarten (Layout-NÄHERUNG).

ACHTUNG: Das ist NICHT der finale, markengenaue Render. Den liefert InDesign
(Datenquelle + Skript). Dieser Code-Renderer dient zum schnellen Testen des
Datenflusses und der zwei Auflösungsstufen:

  - Druck (hoch):  85×55 mm + 3 mm Beschnitt, Schnittmarken, CMYK, Vektor.
  - Proof (niedrig): 85×55 mm, als ~100-dpi-Rasterbild eingebettet (RGB),
                     kleine Datei – wie ein E-Mail-Proof.

Ersatz-Schrift Helvetica (statt Helvetica Neue LT Com), Logo als Platzhalter.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import fitz  # PyMuPDF – zum Rastern
from reportlab.lib.colors import CMYKColor
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from app.feldmapping import auf_merge_felder, variante
from app.xml_import import parse_bestellung

TRIM_W, TRIM_H = 85, 55       # mm
BLEED = 3                      # mm
MARK = 4                       # mm Schnittmarken-Länge
RAND = BLEED + MARK + 1        # mm Außenrand (Druck-Seite)

SCHWARZ = CMYKColor(0, 0, 0, 1)
GRAU = CMYKColor(0, 0, 0, 0.45)
HELLGRAU = CMYKColor(0, 0, 0, 0.25)

FIRMA_TEXT = {
    "Barmag": ["Barmag GmbH & Co. KG"],
    "Neumag": ["Neumag", "Zweigniederlassung der", "Barmag GmbH & Co. KG"],
}


def _zeilen(felder: dict, var: str) -> list[tuple[str, str]]:
    """(stil, text) – stil ∈ {name, sub, firma, body}."""
    name = " ".join(p for p in (felder["Dr."], felder["Vorname"], felder["Name"]) if p).strip()
    z: list[tuple[str, str]] = [("name", name or "—")]
    if felder["Titel"]:
        z.append(("sub", felder["Titel"]))
    if felder["Funktion"]:
        z.append(("sub", felder["Funktion"]))
    z.append(("luecke", ""))
    for fz in FIRMA_TEXT.get(var, [var]):
        z.append(("firma", fz))
    if felder["Straße Hausnummer"]:
        z.append(("body", felder["Straße Hausnummer"]))
    plz_ort = " ".join(p for p in (felder["PLZ"], felder["Ort"]) if p).strip()
    if plz_ort:
        z.append(("body", plz_ort))
    if felder["Land"]:
        z.append(("body", felder["Land"]))
    z.append(("luecke", ""))
    if felder["Phone"]:
        z.append(("body", f"T  {felder['Phone']}"))
    if felder["Mobile"]:
        z.append(("body", f"M  {felder['Mobile']}"))
    if felder["E-Mail"]:
        z.append(("body", felder["E-Mail"]))
    return z


def _zeichne_karte(c: canvas.Canvas, x0: float, y0: float, felder: dict, var: str) -> None:
    """Zeichnet den Karteninhalt; (x0,y0) = linke untere Ecke des Trim-Bereichs (in pt)."""
    # Logo-Platzhalter oben rechts
    c.setStrokeColor(HELLGRAU)
    c.setFillColor(HELLGRAU)
    c.rect(x0 + (TRIM_W - 28) * mm, y0 + (TRIM_H - 12) * mm, 22 * mm, 7 * mm, stroke=1, fill=0)
    c.setFont("Helvetica", 5)
    c.drawCentredString(x0 + (TRIM_W - 17) * mm, y0 + (TRIM_H - 9) * mm, "[Barmag-Logo]")

    lm = x0 + 6 * mm
    y = y0 + (TRIM_H - 9) * mm
    for stil, text in _zeilen(felder, var):
        if stil == "luecke":
            y -= 2.0 * mm
            continue
        if stil == "name":
            c.setFont("Helvetica-Bold", 9); c.setFillColor(SCHWARZ); lh = 4.6 * mm
        elif stil == "sub":
            c.setFont("Helvetica", 7); c.setFillColor(GRAU); lh = 3.4 * mm
        elif stil == "firma":
            c.setFont("Helvetica-Bold", 6.5); c.setFillColor(SCHWARZ); lh = 3.2 * mm
        else:
            c.setFont("Helvetica", 6.5); c.setFillColor(SCHWARZ); lh = 3.2 * mm
        c.drawString(lm, y, text)
        y -= lh


def _schnittmarken(c: canvas.Canvas, x0: float, y0: float) -> None:
    c.setStrokeColor(SCHWARZ)
    c.setLineWidth(0.3)
    tw, th, bl, mk = TRIM_W * mm, TRIM_H * mm, BLEED * mm, MARK * mm
    ecken = [(x0, y0), (x0 + tw, y0), (x0, y0 + th), (x0 + tw, y0 + th)]
    for (ex, ey) in ecken:
        sx = -1 if ex == x0 else 1
        sy = -1 if ey == y0 else 1
        # vertikale Marke
        c.line(ex, ey + sy * bl, ex, ey + sy * (bl + mk))
        # horizontale Marke
        c.line(ex + sx * bl, ey, ex + sx * (bl + mk), ey)


def render_druck(felder: dict, var: str, pfad: str | Path) -> Path:
    pw, ph = (TRIM_W + 2 * RAND) * mm, (TRIM_H + 2 * RAND) * mm
    c = canvas.Canvas(str(pfad), pagesize=(pw, ph))
    x0, y0 = RAND * mm, RAND * mm
    # weißer Beschnitt-/Kartengrund
    c.setFillColor(CMYKColor(0, 0, 0, 0))
    c.rect((RAND - BLEED) * mm, (RAND - BLEED) * mm,
           (TRIM_W + 2 * BLEED) * mm, (TRIM_H + 2 * BLEED) * mm, stroke=0, fill=1)
    _zeichne_karte(c, x0, y0, felder, var)
    _schnittmarken(c, x0, y0)
    c.setTitle("Visitenkarte – Druck (hoch, CMYK, 3 mm Beschnitt)")
    c.save()
    return Path(pfad)


def render_proof(felder: dict, var: str, pfad: str | Path, dpi: int = 100) -> Path:
    # 1) Trim-only Vektor-PDF in temp
    tmp = Path(tempfile.mkdtemp()) / "trim.pdf"
    c = canvas.Canvas(str(tmp), pagesize=(TRIM_W * mm, TRIM_H * mm))
    _zeichne_karte(c, 0, 0, felder, var)
    c.save()
    # 2) niedrig rastern
    doc = fitz.open(str(tmp))
    zoom = dpi / 72.0
    pix = doc[0].get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    png = Path(tempfile.mkdtemp()) / "proof.png"
    pix.save(str(png))
    # 3) Rasterbild in 85×55-PDF einbetten (RGB, klein)
    c2 = canvas.Canvas(str(pfad), pagesize=(TRIM_W * mm, TRIM_H * mm))
    c2.drawImage(str(png), 0, 0, width=TRIM_W * mm, height=TRIM_H * mm)
    c2.setTitle(f"Visitenkarte – Proof (niedrig, ~{dpi} dpi)")
    c2.save()
    return Path(pfad)


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Test-Render (niedrig + hoch) aus Bestell-XML")
    ap.add_argument("xml")
    ap.add_argument("-n", "--nummer", type=int, default=1, help="welche Karte (1-basiert)")
    ap.add_argument("-o", "--out", default="./render_test")
    args = ap.parse_args(argv)

    bestellung = parse_bestellung(args.xml)
    karte = bestellung.karten[args.nummer - 1]
    felder = auf_merge_felder(karte.udx)
    var = variante(karte.udx)
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    name = (felder["Vorname"] + "_" + felder["Name"]).replace(" ", "") or "karte"

    p_lo = render_proof(felder, var, out / f"VK_{name}_proof_niedrig.pdf")
    p_hi = render_druck(felder, var, out / f"VK_{name}_druck_hoch.pdf")
    print(f"Karte: {felder['Vorname']} {felder['Name']} [{var}]")
    print(f"  Proof (niedrig): {p_lo}  ({p_lo.stat().st_size} Bytes)")
    print(f"  Druck (hoch):    {p_hi}  ({p_hi.stat().st_size} Bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
