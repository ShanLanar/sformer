"""Import von openTRANS-2.1-Bestell-XML (Shop 'allago') in Kartendatensätze.

Jede ORDER_ITEM entspricht einer Person/Visitenkarte. Die variablen Inhalte
stehen als PRODUCT_FEATURES/FEATURE-Paare (UDX.DATAFIELDNAME/UDX.DATAFIELDCONTENT).
Der Parser ignoriert Namespaces (openTRANS/BMEcat) und arbeitet über Local-Names.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path


def _lokal(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _text(elem) -> str:
    return (elem.text or "").strip() if elem is not None else ""


def _erstes(elem, name: str):
    for e in elem.iter():
        if _lokal(e.tag) == name:
            return e
    return None


def _alle(elem, name: str):
    return [e for e in elem.iter() if _lokal(e.tag) == name]


@dataclass
class Besteller:
    anrede: str = ""        # TITLE, z. B. "Frau"/"Herr"
    vorname: str = ""       # FIRST_NAME
    nachname: str = ""       # CONTACT_NAME
    email: str = ""
    firma: str = ""

    @property
    def anzeigename(self) -> str:
        return " ".join(p for p in (self.vorname, self.nachname) if p).strip()


@dataclass
class Karte:
    line_id: str
    beschreibung: str
    menge: str
    udx: dict[str, str] = field(default_factory=dict)


@dataclass
class Bestellung:
    order_id: str
    besteller: Besteller
    karten: list[Karte] = field(default_factory=list)


def _besteller_aus(root) -> Besteller:
    """Nimmt die Käufer-Partei mit hinterlegter E-Mail als Proof-Empfänger."""
    bester = Besteller()
    for party in _alle(root, "PARTY"):
        rollen = {_text(r).lower() for r in _alle(party, "PARTY_ROLE")}
        if "supplier" in rollen:
            continue
        cd = _erstes(party, "CONTACT_DETAILS")
        email = _text(_erstes(party, "EMAIL"))
        if cd is None and not email:
            continue
        kandidat = Besteller(
            anrede=_text(_erstes(cd, "TITLE")) if cd is not None else "",
            vorname=_text(_erstes(cd, "FIRST_NAME")) if cd is not None else "",
            nachname=_text(_erstes(cd, "CONTACT_NAME")) if cd is not None else "",
            email=email,
            firma=_text(_erstes(party, "NAME")),
        )
        # Partei mit E-Mail bevorzugen
        if kandidat.email and not bester.email:
            bester = kandidat
        elif not bester.vorname and kandidat.vorname:
            bester = kandidat
    return bester


def _udx_aus_item(item) -> dict[str, str]:
    udx: dict[str, str] = {}
    for feature in _alle(item, "FEATURE"):
        name = _text(_erstes(feature, "UDX.DATAFIELDNAME"))
        if not name:
            continue
        inhalt = _text(_erstes(feature, "UDX.DATAFIELDCONTENT"))
        udx[name.strip().lower()] = inhalt
    return udx


def parse_bestellung(xml_pfad: str | Path) -> Bestellung:
    root = ET.parse(str(xml_pfad)).getroot()
    order_id = _text(_erstes(root, "ORDER_ID"))
    besteller = _besteller_aus(root)

    karten: list[Karte] = []
    for item in _alle(root, "ORDER_ITEM"):
        karten.append(
            Karte(
                line_id=_text(_erstes(item, "LINE_ITEM_ID")),
                beschreibung=_text(_erstes(item, "DESCRIPTION_SHORT")),
                menge=_text(_erstes(item, "QUANTITY")),
                udx=_udx_aus_item(item),
            )
        )
    return Bestellung(order_id=order_id, besteller=besteller, karten=karten)
