"""vCard-3.0-Aufbau für den QR-Code – Muster aus der Barmag-Master-PDF nachgebaut.

Original-Muster (entschlüsselt aus der Vorlage):
    N:Nachname;Vorname;;Titel · FN:… · ORG:Firma;; · TITLE:Funktion(en) ·
    TEL;TYPE=WORK;VOICE:… · TEL;TYPE=CELL:… ·
    ADR;TYPE=WORK:;;Straße;Ort;;PLZ;Land · EMAIL;TYPE=WORK;INTERNET:… · URL:…
Zeilentrenner wie im Original: Carriage Return (\\r).
"""

from __future__ import annotations

from pathlib import Path

import qrcode

URL = "https://www.barmag.com"


def baue_vcard(felder: dict, udx: dict) -> str:
    dr = felder.get("Dr.", "").strip()
    vn = felder.get("Vorname", "").strip()
    nn = felder.get("Name", "").strip()
    fn = " ".join(p for p in (dr, vn, nn) if p)
    org = udx.get("firmenname", "").strip()
    funktionen = [v.strip() for v in (
        udx.get("funktion", ""), udx.get("funktion2", ""),
        udx.get("funktion3", ""), udx.get("funktion4", "")) if v.strip()]
    title = ", ".join(funktionen)

    work = " ".join(p for p in (
        udx.get("vorwahl_telefon_international", "").strip(),
        udx.get("vorwahl_telefon", "").strip(),
        udx.get("telefon", "").strip(),
        udx.get("telefon_durchwahl", "").strip()) if p)
    cell = (udx.get("vorwahl_mobil_international", "").strip() + " "
            + udx.get("vorwahl_mobil", "").strip()
            + udx.get("mobil", "").strip()).strip()

    zeilen = [
        "BEGIN:VCARD", "VERSION:3.0",
        f"N:{nn};{vn};;{dr}",
        f"FN:{fn}",
        f"ORG:{org};;",
        f"TITLE:{title}",
        f"TEL;TYPE=WORK;VOICE:{work}",
        f"TEL;TYPE=CELL:{cell}",
        f"ADR;TYPE=WORK:;;{felder.get('Straße Hausnummer', '').strip()};"
        f"{felder.get('Ort', '').strip()};;{felder.get('PLZ', '').strip()};"
        f"{felder.get('Land', '').strip()}",
        f"EMAIL;TYPE=WORK;INTERNET:{felder.get('E-Mail', '').strip()}",
        f"URL:{URL}",
        "END:VCARD",
    ]
    return "\r".join(zeilen)


def qr_png(text: str, pfad: str | Path, border: int = 2, box_size: int = 24) -> Path:
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,
                       border=border, box_size=box_size)
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    pfad = Path(pfad)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(pfad))
    return pfad
