"""FastAPI-Anwendung: interne Auftragsverwaltung + öffentliche Kundenfreigabe."""

from __future__ import annotations

import re
import secrets
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import einstellungen
from .database import datenbank_initialisieren, get_db
from .email_service import (
    render_freigabe_html,
    sende_freigabe_mail,
    sende_interne_benachrichtigung,
)
from .models import Auftrag, Ereignis, Status, jetzt
from .preflight import kurzfassung, pruefe_pdf

BASIS = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    einstellungen.verzeichnisse_anlegen()
    datenbank_initialisieren()
    yield


app = FastAPI(title=einstellungen.APP_NAME, lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(BASIS / "static")), name="static")

templates = Jinja2Templates(directory=str(BASIS / "templates"))
templates.env.globals["einstellungen"] = einstellungen
templates.env.globals["Status"] = Status


# --------------------------------------------------------------------------- #
# Hilfsfunktionen
# --------------------------------------------------------------------------- #
def _auftrag_holen(db: Session, auftrag_id: int) -> Auftrag | None:
    return db.get(Auftrag, auftrag_id)


def _auftrag_nach_token(db: Session, token: str) -> Auftrag | None:
    return db.scalar(select(Auftrag).where(Auftrag.freigabe_token == token))


def _protokoll(db: Session, auftrag: Auftrag, typ: str, text: str) -> None:
    db.add(Ereignis(auftrag_id=auftrag.id, typ=typ, text=text))


def _naechste_auftragsnummer(db: Session) -> str:
    jahr = jetzt().year
    # Laufende Nummer = bestehende Treffer dieses Jahres + 1
    anzahl = db.scalar(
        select(func.count(Auftrag.id)).where(Auftrag.auftragsnummer.like(f"A-{jahr}-%"))
    )
    return f"A-{jahr}-{(anzahl or 0) + 1:04d}"


def _sicherer_dateiname(name: str) -> str:
    name = Path(name).name
    return re.sub(r"[^A-Za-z0-9._-]", "_", name) or "datei.pdf"


# --------------------------------------------------------------------------- #
# Interne Oberfläche (Vorstufe)
# --------------------------------------------------------------------------- #
@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    auftraege = db.scalars(select(Auftrag).order_by(Auftrag.erstellt_am.desc())).all()
    return templates.TemplateResponse(request, "dashboard.html", {"auftraege": auftraege})


@app.get("/auftrag/neu", response_class=HTMLResponse)
def auftrag_neu_formular(request: Request):
    return templates.TemplateResponse(request, "auftrag_neu.html")


@app.post("/auftrag/neu")
async def auftrag_neu_anlegen(
    db: Session = Depends(get_db),
    titel: str = Form(...),
    kunde_name: str = Form(...),
    kunde_email: str = Form(...),
    format: str = Form(""),
    auflage: int = Form(0),
    beschreibung: str = Form(""),
    pdf: UploadFile | None = File(None),
):
    auftrag = Auftrag(
        auftragsnummer=_naechste_auftragsnummer(db),
        titel=titel.strip(),
        kunde_name=kunde_name.strip(),
        kunde_email=kunde_email.strip(),
        format=format.strip(),
        auflage=auflage,
        beschreibung=beschreibung.strip(),
        status=Status.NEU.value,
    )
    db.add(auftrag)
    db.flush()  # vergibt die id

    if pdf is not None and pdf.filename:
        dateiname = f"{auftrag.auftragsnummer}_{_sicherer_dateiname(pdf.filename)}"
        ziel = einstellungen.UPLOAD_DIR / dateiname
        ziel.write_bytes(await pdf.read())
        auftrag.pdf_dateiname = pdf.filename
        auftrag.pdf_pfad = str(ziel)
        _protokoll(db, auftrag, "upload", f"PDF hochgeladen: {pdf.filename}")

    _protokoll(db, auftrag, "angelegt", f"Auftrag {auftrag.auftragsnummer} angelegt.")
    db.commit()
    return RedirectResponse(f"/auftrag/{auftrag.id}", status_code=303)


@app.get("/auftrag/{auftrag_id}", response_class=HTMLResponse)
def auftrag_detail(auftrag_id: int, request: Request, db: Session = Depends(get_db)):
    auftrag = _auftrag_holen(db, auftrag_id)
    if auftrag is None:
        return HTMLResponse("Auftrag nicht gefunden.", status_code=404)

    preflight = None
    if auftrag.pdf_pfad:
        ergebnis = pruefe_pdf(auftrag.pdf_pfad)
        preflight = {"ergebnis": ergebnis, "text": kurzfassung(ergebnis)}

    freigabe_url = None
    if auftrag.freigabe_token:
        freigabe_url = f"{einstellungen.BASE_URL}/freigabe/{auftrag.freigabe_token}"

    return templates.TemplateResponse(
        request,
        "auftrag_detail.html",
        {
            "auftrag": auftrag,
            "preflight": preflight,
            "freigabe_url": freigabe_url,
        },
    )


@app.get("/auftrag/{auftrag_id}/pdf")
def auftrag_pdf(auftrag_id: int, db: Session = Depends(get_db)):
    auftrag = _auftrag_holen(db, auftrag_id)
    if auftrag is None or not auftrag.pdf_pfad or not Path(auftrag.pdf_pfad).exists():
        return HTMLResponse("Keine PDF-Datei.", status_code=404)
    return FileResponse(auftrag.pdf_pfad, media_type="application/pdf",
                        filename=auftrag.pdf_dateiname or "druckdaten.pdf")


@app.post("/auftrag/{auftrag_id}/status")
def auftrag_status_setzen(
    auftrag_id: int,
    db: Session = Depends(get_db),
    status: str = Form(...),
):
    auftrag = _auftrag_holen(db, auftrag_id)
    if auftrag is None:
        return HTMLResponse("Auftrag nicht gefunden.", status_code=404)
    try:
        neuer = Status(status)
    except ValueError:
        return HTMLResponse("Ungültiger Status.", status_code=400)

    alt = auftrag.status_enum.label
    auftrag.status = neuer.value
    _protokoll(db, auftrag, "status", f"Status: {alt} → {neuer.label}")
    db.commit()
    return RedirectResponse(f"/auftrag/{auftrag_id}", status_code=303)


@app.post("/auftrag/{auftrag_id}/freigabe-senden")
def freigabe_senden(auftrag_id: int, db: Session = Depends(get_db)):
    auftrag = _auftrag_holen(db, auftrag_id)
    if auftrag is None:
        return HTMLResponse("Auftrag nicht gefunden.", status_code=404)
    if not auftrag.kunde_email:
        return HTMLResponse("Keine Kunden-E-Mail hinterlegt.", status_code=400)

    auftrag.freigabe_token = secrets.token_urlsafe(32)
    auftrag.freigabe_token_ablauf = jetzt() + timedelta(
        days=einstellungen.FREIGABE_GUELTIGKEIT_TAGE
    )
    auftrag.freigabe_versendet_am = jetzt()
    auftrag.freigabe_entscheidung_am = None
    auftrag.freigabe_kommentar = None
    auftrag.status = Status.FREIGABE_VERSENDET.value

    meldung = sende_freigabe_mail(auftrag)
    _protokoll(db, auftrag, "freigabe_gesendet",
               f"Freigabe-Mail an {auftrag.kunde_email}. {meldung}")
    db.commit()
    return RedirectResponse(f"/auftrag/{auftrag_id}", status_code=303)


# --------------------------------------------------------------------------- #
# Öffentliche Kundenfreigabe (ohne Login)
# --------------------------------------------------------------------------- #
@app.get("/freigabe/{token}", response_class=HTMLResponse)
def freigabe_seite(token: str, request: Request, db: Session = Depends(get_db)):
    auftrag = _auftrag_nach_token(db, token)
    if auftrag is None:
        return templates.TemplateResponse(
            request, "freigabe_fehler.html",
            {"grund": "Dieser Freigabe-Link ist ungültig."},
            status_code=404,
        )
    if auftrag.freigabe_entscheidung_am is not None:
        return templates.TemplateResponse(request, "freigabe_done.html", {"auftrag": auftrag})
    if not auftrag.freigabe_aktiv:
        return templates.TemplateResponse(
            request, "freigabe_fehler.html",
            {"grund": "Dieser Freigabe-Link ist abgelaufen."},
            status_code=410,
        )
    return templates.TemplateResponse(
        request, "freigabe.html", {"auftrag": auftrag, "token": token}
    )


@app.get("/freigabe/{token}/pdf")
def freigabe_pdf(token: str, db: Session = Depends(get_db)):
    auftrag = _auftrag_nach_token(db, token)
    if auftrag is None or not auftrag.pdf_pfad or not Path(auftrag.pdf_pfad).exists():
        return HTMLResponse("Keine PDF-Datei.", status_code=404)
    return FileResponse(auftrag.pdf_pfad, media_type="application/pdf",
                        filename=auftrag.pdf_dateiname or "druckdaten.pdf")


@app.post("/freigabe/{token}")
def freigabe_verarbeiten(
    token: str,
    request: Request,
    db: Session = Depends(get_db),
    entscheidung: str = Form(...),
    kommentar: str = Form(""),
):
    auftrag = _auftrag_nach_token(db, token)
    if auftrag is None or not auftrag.freigabe_aktiv:
        return templates.TemplateResponse(
            request, "freigabe_fehler.html",
            {"grund": "Dieser Freigabe-Link ist nicht mehr gültig."},
            status_code=410,
        )
    if auftrag.freigabe_entscheidung_am is not None:
        return templates.TemplateResponse(request, "freigabe_done.html", {"auftrag": auftrag})

    auftrag.freigabe_entscheidung_am = jetzt()
    auftrag.freigabe_kommentar = kommentar.strip() or None

    if entscheidung == "freigeben":
        auftrag.status = Status.FREIGEGEBEN.value
        typ, info = "freigegeben", "Kunde hat den Auftrag freigegeben."
    else:
        auftrag.status = Status.AENDERUNG_ANGEFORDERT.value
        typ, info = "aenderung", "Kunde hat eine Änderung angefordert."

    if auftrag.freigabe_kommentar:
        info += f" Kommentar: {auftrag.freigabe_kommentar}"
    _protokoll(db, auftrag, typ, info)

    sende_interne_benachrichtigung(
        auftrag,
        betreff=f"[{auftrag.status_enum.label}] {auftrag.auftragsnummer} – {auftrag.titel}",
        text=info,
    )
    db.commit()
    return templates.TemplateResponse(request, "freigabe_done.html", {"auftrag": auftrag})


# Vorschau der Freigabe-Mail im Browser (praktisch beim Anpassen des Layouts).
@app.get("/auftrag/{auftrag_id}/mail-vorschau", response_class=HTMLResponse)
def mail_vorschau(auftrag_id: int, db: Session = Depends(get_db)):
    auftrag = _auftrag_holen(db, auftrag_id)
    if auftrag is None:
        return HTMLResponse("Auftrag nicht gefunden.", status_code=404)
    if not auftrag.freigabe_token:
        # Temporären Token nur für die Vorschau setzen (nicht speichern).
        auftrag.freigabe_token = "vorschau-token"
        auftrag.freigabe_token_ablauf = jetzt() + timedelta(days=einstellungen.FREIGABE_GUELTIGKEIT_TAGE)
    return HTMLResponse(render_freigabe_html(auftrag))
