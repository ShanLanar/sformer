"""Datenbankmodelle und Status-Workflow."""

from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def jetzt() -> datetime:
    """Aktueller Zeitpunkt als naive UTC – konsistent über SQLite hinweg."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Basis(DeclarativeBase):
    pass


class Status(str, enum.Enum):
    """Status-Workflow eines Auftrags."""

    NEU = "neu"
    IN_VORSTUFE = "in_vorstufe"
    FREIGABE_VERSENDET = "freigabe_versendet"
    FREIGEGEBEN = "freigegeben"
    AENDERUNG_ANGEFORDERT = "aenderung_angefordert"
    IN_PRODUKTION = "in_produktion"
    ABGESCHLOSSEN = "abgeschlossen"

    @property
    def label(self) -> str:
        return {
            Status.NEU: "Neu",
            Status.IN_VORSTUFE: "In Vorstufe",
            Status.FREIGABE_VERSENDET: "Freigabe versendet",
            Status.FREIGEGEBEN: "Freigegeben",
            Status.AENDERUNG_ANGEFORDERT: "Änderung angefordert",
            Status.IN_PRODUKTION: "In Produktion",
            Status.ABGESCHLOSSEN: "Abgeschlossen",
        }[self]

    @property
    def farbe(self) -> str:
        """Badge-Farbe für die Oberfläche."""
        return {
            Status.NEU: "#6c757d",
            Status.IN_VORSTUFE: "#0d6efd",
            Status.FREIGABE_VERSENDET: "#E8930A",
            Status.FREIGEGEBEN: "#198754",
            Status.AENDERUNG_ANGEFORDERT: "#dc3545",
            Status.IN_PRODUKTION: "#6f42c1",
            Status.ABGESCHLOSSEN: "#212529",
        }[self]


class Auftrag(Basis):
    __tablename__ = "auftraege"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    auftragsnummer: Mapped[str] = mapped_column(String(32), unique=True, index=True)

    titel: Mapped[str] = mapped_column(String(200))
    kunde_name: Mapped[str] = mapped_column(String(200))
    kunde_email: Mapped[str] = mapped_column(String(200))

    format: Mapped[str] = mapped_column(String(60), default="")
    auflage: Mapped[int] = mapped_column(Integer, default=0)
    beschreibung: Mapped[str] = mapped_column(Text, default="")

    pdf_dateiname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pdf_pfad: Mapped[str | None] = mapped_column(String(500), nullable=True)

    status: Mapped[str] = mapped_column(String(40), default=Status.NEU.value, index=True)

    # Freigabe-Vorgang
    freigabe_token: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True, index=True)
    freigabe_token_ablauf: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    freigabe_versendet_am: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    freigabe_entscheidung_am: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    freigabe_kommentar: Mapped[str | None] = mapped_column(Text, nullable=True)

    erstellt_am: Mapped[datetime] = mapped_column(DateTime, default=jetzt)
    aktualisiert_am: Mapped[datetime] = mapped_column(DateTime, default=jetzt, onupdate=jetzt)

    ereignisse: Mapped[list["Ereignis"]] = relationship(
        back_populates="auftrag",
        cascade="all, delete-orphan",
        order_by="Ereignis.zeitpunkt.desc()",
    )

    @property
    def status_enum(self) -> Status:
        return Status(self.status)

    @property
    def freigabe_aktiv(self) -> bool:
        """True, wenn ein gültiger (nicht abgelaufener) Freigabe-Token existiert."""
        if not self.freigabe_token or not self.freigabe_token_ablauf:
            return False
        return self.freigabe_token_ablauf > jetzt()


class Ereignis(Basis):
    """Audit-Trail / Protokoll-Eintrag zu einem Auftrag."""

    __tablename__ = "ereignisse"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    auftrag_id: Mapped[int] = mapped_column(ForeignKey("auftraege.id", ondelete="CASCADE"), index=True)
    zeitpunkt: Mapped[datetime] = mapped_column(DateTime, default=jetzt)
    typ: Mapped[str] = mapped_column(String(40))
    text: Mapped[str] = mapped_column(Text, default="")

    auftrag: Mapped[Auftrag] = relationship(back_populates="ereignisse")
