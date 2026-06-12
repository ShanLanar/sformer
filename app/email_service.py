"""E-Mail-Versand für den Freigabe-Workflow.

Rendert die ABE-gebrandete HTML-Mail und verschickt sie via SMTP. Ist SMTP
nicht aktiviert (Standard), wird die Mail als ``.eml`` in die Outbox
geschrieben – so lässt sich der komplette Ablauf ohne Mailserver testen.
"""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .config import einstellungen
from .models import Auftrag

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


def _freigabe_url(auftrag: Auftrag) -> str:
    return f"{einstellungen.BASE_URL}/freigabe/{auftrag.freigabe_token}"


def render_freigabe_html(auftrag: Auftrag) -> str:
    """Rendert die HTML-Mail – auch einzeln nutzbar (z. B. für Vorschau)."""
    template = _env.get_template("email_freigabe.html")
    return template.render(
        auftrag=auftrag,
        freigabe_url=_freigabe_url(auftrag),
        einstellungen=einstellungen,
        ablauf=auftrag.freigabe_token_ablauf,
    )


def _plaintext(auftrag: Auftrag) -> str:
    return (
        f"Freigabe-Anfrage für Auftrag {auftrag.auftragsnummer}: {auftrag.titel}\n\n"
        f"Bitte prüfen und freigeben:\n{_freigabe_url(auftrag)}\n\n"
        f"Der Link ist gültig bis "
        f"{auftrag.freigabe_token_ablauf:%d.%m.%Y} (sofern gesetzt).\n\n"
        f"{einstellungen.FIRMA} – {einstellungen.APP_NAME}"
    )


def _nachricht_bauen(auftrag: Auftrag) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = f"Druckfreigabe erforderlich – {auftrag.titel} ({auftrag.auftragsnummer})"
    msg["From"] = formataddr((einstellungen.SMTP_FROM_NAME, einstellungen.SMTP_FROM))
    msg["To"] = auftrag.kunde_email
    msg.set_content(_plaintext(auftrag))
    msg.add_alternative(render_freigabe_html(auftrag), subtype="html")
    return msg


def _in_outbox_schreiben(msg: EmailMessage, auftrag: Auftrag) -> Path:
    einstellungen.verzeichnisse_anlegen()
    ziel = einstellungen.OUTBOX_DIR / f"freigabe_{auftrag.auftragsnummer}.eml"
    ziel.write_bytes(bytes(msg))
    return ziel


def sende_freigabe_mail(auftrag: Auftrag) -> str:
    """Verschickt (oder speichert) die Freigabe-Mail.

    Rückgabe: kurze Statusmeldung für das Protokoll.
    """
    msg = _nachricht_bauen(auftrag)

    if not einstellungen.SMTP_ENABLED:
        ziel = _in_outbox_schreiben(msg, auftrag)
        return f"Mail (Dev-Modus) in Outbox geschrieben: {ziel.name}"

    with smtplib.SMTP(einstellungen.SMTP_HOST, einstellungen.SMTP_PORT) as server:
        if einstellungen.SMTP_USE_TLS:
            server.starttls()
        if einstellungen.SMTP_USER:
            server.login(einstellungen.SMTP_USER, einstellungen.SMTP_PASSWORD)
        server.send_message(msg)
    return f"Freigabe-Mail an {auftrag.kunde_email} versendet."


def sende_interne_benachrichtigung(auftrag: Auftrag, betreff: str, text: str) -> None:
    """Optionale Info-Mail an die Vorstufe, sobald der Kunde entscheidet."""
    empfaenger = einstellungen.BENACHRICHTIGUNG_AN
    if not empfaenger:
        return

    msg = EmailMessage()
    msg["Subject"] = betreff
    msg["From"] = formataddr((einstellungen.SMTP_FROM_NAME, einstellungen.SMTP_FROM))
    msg["To"] = empfaenger
    msg.set_content(text)

    if not einstellungen.SMTP_ENABLED:
        ziel = einstellungen.OUTBOX_DIR / f"info_{auftrag.auftragsnummer}.eml"
        ziel.write_bytes(bytes(msg))
        return

    with smtplib.SMTP(einstellungen.SMTP_HOST, einstellungen.SMTP_PORT) as server:
        if einstellungen.SMTP_USE_TLS:
            server.starttls()
        if einstellungen.SMTP_USER:
            server.login(einstellungen.SMTP_USER, einstellungen.SMTP_PASSWORD)
        server.send_message(msg)
