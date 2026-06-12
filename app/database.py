"""Datenbank-Anbindung (SQLite via SQLAlchemy)."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import einstellungen
from .models import Basis

einstellungen.verzeichnisse_anlegen()

engine = create_engine(
    f"sqlite:///{einstellungen.DB_PFAD}",
    connect_args={"check_same_thread": False},
)
SessionLokal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def datenbank_initialisieren() -> None:
    """Legt die Tabellen an, falls sie noch nicht existieren."""
    Basis.metadata.create_all(bind=engine)


def get_db() -> Iterator[Session]:
    """FastAPI-Dependency: liefert eine Session und schließt sie sauber."""
    db = SessionLokal()
    try:
        yield db
    finally:
        db.close()
