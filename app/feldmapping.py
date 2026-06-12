"""Abbildung der XML-UDX-Felder auf die InDesign-Data-Merge-Platzhalter.

Die InDesign-Master-Vorlage nutzt diese Platzhalter (ohne <<>>):
    Dr. · Vorname · Name · Titel · Funktion · Straße Hausnummer ·
    PLZ · Ort · Land · Phone · Mobile · E-Mail

Aus den feingranularen XML-Feldern werden Telefon/Mobil/E-Mail zusammengesetzt
und die richtige Vorlagen-Variante (Barmag/Neumag) bestimmt.

ANNAHMEN (bitte fachlich bestätigen):
- Titel  ← erste belegte Funktionszeile (funktion/funktion2/…)
- Funktion ← zweite belegte Funktionszeile
- Land wird unverändert übernommen ("Germany" → ggf. "Deutschland" gewünscht?)
- Telefon-Format: "<intl> <vorwahl> <nummer>-<durchwahl>"
"""

from __future__ import annotations

# Reihenfolge/Schreibweise EXAKT wie die <<Platzhalter>> in der Vorlage:
MERGE_FELDER = [
    "Dr.", "Vorname", "Name", "Titel", "Funktion",
    "Straße Hausnummer", "PLZ", "Ort", "Land",
    "Phone", "Mobile", "E-Mail",
]


def _join(parts, sep: str = " ") -> str:
    return sep.join(p for p in (str(x).strip() for x in parts) if p)


def telefon(udx: dict) -> str:
    nummer = udx.get("telefon", "").strip()
    durchwahl = udx.get("telefon_durchwahl", "").strip()
    basis = _join([nummer, durchwahl], "-") if durchwahl else nummer
    return _join([udx.get("vorwahl_telefon_international", ""),
                  udx.get("vorwahl_telefon", ""), basis])


def mobil(udx: dict) -> str:
    return _join([udx.get("vorwahl_mobil_international", ""),
                  udx.get("vorwahl_mobil", ""),
                  udx.get("mobil", "")])


def email(udx: dict) -> str:
    return (udx.get("email_user", "").strip() + udx.get("email_domain", "").strip())


def _funktionen(udx: dict) -> list[str]:
    return [v for v in (
        udx.get("funktion", ""), udx.get("funktion2", ""),
        udx.get("funktion3", ""), udx.get("funktion4", ""),
    ) if v.strip()]


def variante(udx: dict) -> str:
    """Bestimmt die Vorlagen-Variante anhand der Firmenbezeichnung."""
    firma = " ".join([udx.get("firmenname", ""), udx.get("firma2", ""),
                      udx.get("firma3", "")]).lower()
    if "neumag" in firma:
        return "Neumag"
    return "Barmag"


def auf_merge_felder(udx: dict) -> dict[str, str]:
    funk = _funktionen(udx)
    return {
        "Dr.": udx.get("namenstitel", ""),
        "Vorname": udx.get("vorname", ""),
        "Name": udx.get("nachname", ""),
        "Titel": funk[0] if len(funk) >= 1 else "",
        "Funktion": funk[1] if len(funk) >= 2 else "",
        "Straße Hausnummer": udx.get("strasse", ""),
        "PLZ": udx.get("plz", ""),
        "Ort": udx.get("ort", ""),
        "Land": udx.get("land", ""),
        "Phone": telefon(udx),
        "Mobile": mobil(udx),
        "E-Mail": email(udx),
    }
