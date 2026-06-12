# ABE Druckvorstufe

Schlankes Workflow-Tool für die Druckvorstufe: **Auftragsdatenbank**,
**Status-Workflow** und **Kundenfreigabe per E-Mail** – ohne Login für den
Kunden, im ABE-Corporate-Design (Orange `#E8930A` / Anthrazit `#2D2D2D`).

Gebaut mit FastAPI + SQLite + Jinja2. Läuft nativ unter Windows, eine
Einzelnutzerin kann es allein bedienen.

---

## Was es kann (Stand 0.1)

- **Auftragserfassung** über eine einfache Weboberfläche (Titel, Kunde, Format,
  Auflage, Notizen, PDF-Upload).
- **Auftragsdatenbank** mit Status-Workflow:
  `Neu → In Vorstufe → Freigabe versendet → Freigegeben / Änderung angefordert
  → In Produktion → Abgeschlossen`.
- **E-Mail-Freigabe**: Auf Knopfdruck wird ein einmaliger Link erzeugt und eine
  ABE-gebrandete Mail an den Kunden geschickt. Der Kunde klickt, sieht eine
  PDF-Vorschau und gibt frei oder fordert eine Änderung an – ganz ohne Konto.
- **Protokoll / Audit-Trail** pro Auftrag (wer/was/wann).
- **Preflight-Basisprüfung** des PDFs (Seitenzahl, Seitenformat in mm).
- **Dev-Modus ohne Mailserver**: Ohne SMTP-Konfiguration werden E-Mails als
  `.eml`-Datei in den Ordner `outbox/` geschrieben – ideal zum Ausprobieren.

### Noch nicht enthalten (bewusst)

Die **Bogenoptimierung / Imposition** (Nutzen verschachteln, Sammelformen,
Schnitt-/Passermarken) ist der fachlich schwierige Teil und ist hier **noch
nicht** umgesetzt. Sie lässt sich später als eigenes Modul ergänzen – siehe
[Roadmap](#roadmap).

---

## Schnellstart unter Windows

Benötigt wird **Python 3.11 oder neuer** (beim Installieren „Add Python to PATH"
anhaken).

### Variante A – mit der Start-Datei (am einfachsten)

Im Projektordner einfach **`run.bat`** doppelklicken. Das Skript legt beim ersten
Start automatisch eine virtuelle Umgebung an, installiert alles Nötige und
startet den Server.

Danach im Browser öffnen: **http://localhost:8000**

### Variante B – von Hand

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## Konfiguration

Standardmäßig läuft alles ohne Konfiguration (Dev-Modus, Mails landen in
`outbox/`). Für den echten Betrieb eine Datei **`.env`** anlegen – als Vorlage
dient `.env.example`:

```bat
copy .env.example .env
```

Die wichtigsten Werte:

| Schlüssel | Bedeutung |
|---|---|
| `BASE_URL` | Adresse, die im Freigabe-Link steht. Muss für den Kunden **von außen erreichbar** sein (VPS oder Portfreigabe im Router). |
| `SMTP_ENABLED` | `true` = echter Mailversand, `false` = Mails in `outbox/`. |
| `SMTP_HOST/PORT/USER/PASSWORD` | Zugangsdaten des Postausgangsservers (z. B. Firmen-SMTP oder ein dediziertes Postfach). |
| `FREIGABE_GUELTIGKEIT_TAGE` | Wie lange der Freigabe-Link gültig ist (Standard 7). |
| `BENACHRICHTIGUNG_AN` | Optionale interne Adresse, die informiert wird, sobald der Kunde entscheidet. |

> **Hinweis zur Erreichbarkeit:** Nur der Moment, in dem der Kunde den Link
> anklickt, erfordert Erreichbarkeit von außen. Intern reicht `localhost`.
> Für den Kundenzugang von außen empfiehlt sich ein kleiner VPS (z. B. Hetzner
> ~4 €/Monat) oder eine Portweiterleitung.

---

## Bedienung in Kürze

1. **Neuer Auftrag** → Daten erfassen, PDF hochladen.
2. Auf der Auftragsseite **„Freigabe-Mail senden"** klicken.
   - Im Dev-Modus liegt die Mail anschließend als `.eml` in `outbox/` und lässt
     sich mit jedem Mailprogramm öffnen.
   - **„Mail-Vorschau"** zeigt das Layout direkt im Browser.
3. Der Kunde öffnet den Link, prüft die Vorschau und entscheidet.
4. Der Status aktualisiert sich automatisch; alles steht im **Protokoll**.

---

## Projektstruktur

```
app/
  main.py            FastAPI-App, Routen (intern + öffentliche Freigabe)
  models.py          Datenmodell (Auftrag, Ereignis) + Status-Workflow
  database.py        SQLite-Anbindung
  config.py          Einstellungen (.env / Umgebungsvariablen)
  email_service.py   Aufbau & Versand der Freigabe-Mail (SMTP oder Outbox)
  preflight.py       PDF-Basisprüfung (Seitenzahl, Format)
  templates/         HTML (Oberfläche, Freigabeseiten, E-Mail-Template)
  static/style.css   Corporate Design
tests/               End-to-End-Test des Freigabe-Workflows
run.bat              Start unter Windows
```

---

## Tests

```bat
pip install pytest httpx
python -m pytest
```

---

## Roadmap

- [ ] PDF-Preflight ausbauen (Farbraum, Beschnitt/Bleed, Schriften, Auflösung)
- [ ] Bogenoptimierung / Imposition als eigenes Modul
      (einfache Schemata selbst, komplexes Nesting ggf. via Spezialbibliothek)
- [ ] Hotfolder-/FTP-Übergabe an die Produktion
- [ ] Mehrbenutzer-Betrieb (falls die Vorstufe wächst)
