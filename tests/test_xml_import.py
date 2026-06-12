"""Test der XML→InDesign-Pipeline mit synthetischen Daten (keine echten PII)."""

import tempfile
from pathlib import Path

from app.datamerge import schreibe_datenquelle
from app.feldmapping import auf_merge_felder, variante
from app.xml_import import parse_bestellung

BEISPIEL_XML = """<?xml version="1.0" encoding="utf-8"?>
<ORDER type="standard" version="2.1"
       xmlns="http://www.opentrans.org/XMLSchema/2.1"
       xmlns:bmecat="http://www.bmecat.org/bmecat/2005">
  <ORDER_HEADER><ORDER_INFO>
    <ORDER_ID>99001122</ORDER_ID>
    <PARTIES><PARTY>
      <PARTY_ROLE>buyer</PARTY_ROLE>
      <ADDRESS>
        <bmecat:NAME>Muster GmbH</bmecat:NAME>
        <CONTACT_DETAILS>
          <bmecat:CONTACT_NAME>Musterfrau</bmecat:CONTACT_NAME>
          <bmecat:FIRST_NAME>Erika</bmecat:FIRST_NAME>
          <bmecat:TITLE>Frau</bmecat:TITLE>
        </CONTACT_DETAILS>
        <bmecat:EMAIL>erika.musterfrau@example.com</bmecat:EMAIL>
      </ADDRESS>
    </PARTY></PARTIES>
  </ORDER_INFO></ORDER_HEADER>
  <ORDER_ITEM_LIST><ORDER_ITEM>
    <LINE_ITEM_ID>1</LINE_ITEM_ID>
    <PRODUCT_ID><bmecat:DESCRIPTION_SHORT lang="deu">Visitenkarten</bmecat:DESCRIPTION_SHORT></PRODUCT_ID>
    <PRODUCT_FEATURES>
      <FEATURE><UDX.DATAFIELDNAME>firmenname </UDX.DATAFIELDNAME><UDX.DATAFIELDCONTENT>Muster GmbH</UDX.DATAFIELDCONTENT></FEATURE>
      <FEATURE><UDX.DATAFIELDNAME>vorname </UDX.DATAFIELDNAME><UDX.DATAFIELDCONTENT>Max</UDX.DATAFIELDCONTENT></FEATURE>
      <FEATURE><UDX.DATAFIELDNAME>nachname </UDX.DATAFIELDNAME><UDX.DATAFIELDCONTENT>Mustermann</UDX.DATAFIELDCONTENT></FEATURE>
      <FEATURE><UDX.DATAFIELDNAME>funktion2 </UDX.DATAFIELDNAME><UDX.DATAFIELDCONTENT>Sales Manager</UDX.DATAFIELDCONTENT></FEATURE>
      <FEATURE><UDX.DATAFIELDNAME>strasse </UDX.DATAFIELDNAME><UDX.DATAFIELDCONTENT>Musterweg 1</UDX.DATAFIELDCONTENT></FEATURE>
      <FEATURE><UDX.DATAFIELDNAME>plz </UDX.DATAFIELDNAME><UDX.DATAFIELDCONTENT>12345</UDX.DATAFIELDCONTENT></FEATURE>
      <FEATURE><UDX.DATAFIELDNAME>ort</UDX.DATAFIELDNAME><UDX.DATAFIELDCONTENT>Musterstadt</UDX.DATAFIELDCONTENT></FEATURE>
      <FEATURE><UDX.DATAFIELDNAME>vorwahl_telefon_international </UDX.DATAFIELDNAME><UDX.DATAFIELDCONTENT>+49</UDX.DATAFIELDCONTENT></FEATURE>
      <FEATURE><UDX.DATAFIELDNAME>vorwahl_telefon </UDX.DATAFIELDNAME><UDX.DATAFIELDCONTENT>30</UDX.DATAFIELDCONTENT></FEATURE>
      <FEATURE><UDX.DATAFIELDNAME>telefon </UDX.DATAFIELDNAME><UDX.DATAFIELDCONTENT>123</UDX.DATAFIELDCONTENT></FEATURE>
      <FEATURE><UDX.DATAFIELDNAME>telefon_durchwahl </UDX.DATAFIELDNAME><UDX.DATAFIELDCONTENT>456</UDX.DATAFIELDCONTENT></FEATURE>
      <FEATURE><UDX.DATAFIELDNAME>email_user </UDX.DATAFIELDNAME><UDX.DATAFIELDCONTENT>max.mustermann</UDX.DATAFIELDCONTENT></FEATURE>
      <FEATURE><UDX.DATAFIELDNAME>email_domain </UDX.DATAFIELDNAME><UDX.DATAFIELDCONTENT>@example.com</UDX.DATAFIELDCONTENT></FEATURE>
    </PRODUCT_FEATURES>
  </ORDER_ITEM></ORDER_ITEM_LIST>
</ORDER>"""


def _xml_datei():
    pfad = Path(tempfile.mkdtemp()) / "bestellung.xml"
    pfad.write_text(BEISPIEL_XML, encoding="utf-8")
    return pfad


def test_parse_und_mapping():
    bestellung = parse_bestellung(_xml_datei())
    assert bestellung.order_id == "99001122"
    assert bestellung.besteller.email == "erika.musterfrau@example.com"
    assert bestellung.besteller.anzeigename == "Erika Musterfrau"
    assert len(bestellung.karten) == 1

    felder = auf_merge_felder(bestellung.karten[0].udx)
    assert felder["Vorname"] == "Max"
    assert felder["Name"] == "Mustermann"
    assert felder["Titel"] == "Sales Manager"      # erste belegte Funktion
    assert felder["Straße Hausnummer"] == "Musterweg 1"
    assert felder["Phone"] == "+49 30 123-456"
    assert felder["E-Mail"] == "max.mustermann@example.com"
    assert variante(bestellung.karten[0].udx) == "Barmag"


def test_datenquelle_ist_utf16_bom():
    bestellung = parse_bestellung(_xml_datei())
    felder = auf_merge_felder(bestellung.karten[0].udx)
    ziel = Path(tempfile.mkdtemp()) / "merge.txt"
    schreibe_datenquelle([felder], ziel)

    rohdaten = ziel.read_bytes()
    assert rohdaten[:2] == b"\xff\xfe"               # UTF-16LE-BOM
    text = rohdaten.decode("utf-16")
    zeilen = text.splitlines()
    assert zeilen[0].split("\t")[:3] == ["Dr.", "Vorname", "Name"]
    assert "Max" in zeilen[1]
