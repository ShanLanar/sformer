"""End-to-End-Test des Kern-Workflows: Auftrag → Freigabe-Mail → Kundenfreigabe."""

import os
import tempfile

# Temporäres Datenverzeichnis VOR dem Import der App setzen (Config liest beim Import).
_TMP = tempfile.mkdtemp(prefix="abe_test_")
os.environ["DATA_DIR"] = os.path.join(_TMP, "data")
os.environ["OUTBOX_DIR"] = os.path.join(_TMP, "outbox")
os.environ["SMTP_ENABLED"] = "false"
os.environ["BASE_URL"] = "http://testserver"

from fastapi.testclient import TestClient  # noqa: E402

from app.database import SessionLokal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Auftrag, Ereignis, Status  # noqa: E402


def _neuen_auftrag_anlegen(client) -> int:
    resp = client.post(
        "/auftrag/neu",
        data={
            "titel": "Visitenkarten Mustermann",
            "kunde_name": "Mustermann GmbH",
            "kunde_email": "kunde@example.com",
            "format": "85x55 mm",
            "auflage": "500",
            "beschreibung": "matt cellophaniert",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303, resp.text
    # Location: /auftrag/{id}
    return int(resp.headers["location"].rsplit("/", 1)[1])


def test_kompletter_freigabe_workflow():
    with TestClient(app) as client:
        auftrag_id = _neuen_auftrag_anlegen(client)

        # Auftrag erscheint auf dem Dashboard
        dash = client.get("/")
        assert "Visitenkarten Mustermann" in dash.text

        # Freigabe-Mail auslösen
        resp = client.post(f"/auftrag/{auftrag_id}/freigabe-senden", follow_redirects=False)
        assert resp.status_code == 303

        # Token + Status aus der DB lesen
        with SessionLokal() as db:
            auftrag = db.get(Auftrag, auftrag_id)
            assert auftrag.status == Status.FREIGABE_VERSENDET.value
            assert auftrag.freigabe_token
            token = auftrag.freigabe_token

        # Outbox-Datei wurde geschrieben (Dev-Modus)
        outbox = os.environ["OUTBOX_DIR"]
        assert any(f.endswith(".eml") for f in os.listdir(outbox))

        # Kunde öffnet die Freigabe-Seite
        seite = client.get(f"/freigabe/{token}")
        assert seite.status_code == 200
        assert "Druckfreigabe" in seite.text

        # Kunde gibt frei (mit Kommentar)
        ergebnis = client.post(
            f"/freigabe/{token}",
            data={"entscheidung": "freigeben", "kommentar": "Passt, danke!"},
        )
        assert ergebnis.status_code == 200
        assert "Vielen Dank" in ergebnis.text

        # DB-Status geprüft
        with SessionLokal() as db:
            auftrag = db.get(Auftrag, auftrag_id)
            assert auftrag.status == Status.FREIGEGEBEN.value
            assert auftrag.freigabe_entscheidung_am is not None
            assert auftrag.freigabe_kommentar == "Passt, danke!"
            typen = [e.typ for e in db.query(Ereignis).filter_by(auftrag_id=auftrag_id)]
            assert "freigegeben" in typen


def test_ungueltiger_token():
    with TestClient(app) as client:
        resp = client.get("/freigabe/gibtsnicht")
        assert resp.status_code == 404
        assert "ungültig" in resp.text.lower()


def test_doppelte_freigabe_wird_abgewiesen():
    with TestClient(app) as client:
        auftrag_id = _neuen_auftrag_anlegen(client)
        client.post(f"/auftrag/{auftrag_id}/freigabe-senden", follow_redirects=False)
        with SessionLokal() as db:
            token = db.get(Auftrag, auftrag_id).freigabe_token

        client.post(f"/freigabe/{token}", data={"entscheidung": "freigeben"})
        # Zweiter Versuch: zeigt die Bestätigungsseite, ändert aber nichts mehr
        zweite = client.post(f"/freigabe/{token}", data={"entscheidung": "aenderung"})
        assert zweite.status_code == 200
        with SessionLokal() as db:
            assert db.get(Auftrag, auftrag_id).status == Status.FREIGEGEBEN.value
