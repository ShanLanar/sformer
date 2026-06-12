@echo off
REM ============================================================
REM  ABE Druckvorstufe - Start unter Windows
REM  Legt beim ersten Start eine virtuelle Umgebung an,
REM  installiert die Abhaengigkeiten und startet den Server.
REM ============================================================
setlocal

cd /d "%~dp0"

if not exist ".venv" (
  echo [Setup] Erstelle virtuelle Umgebung ...
  python -m venv .venv
  call .venv\Scripts\activate.bat
  echo [Setup] Installiere Abhaengigkeiten ...
  python -m pip install --upgrade pip
  pip install -r requirements.txt
) else (
  call .venv\Scripts\activate.bat
)

echo.
echo [Start] Server laeuft auf http://localhost:8000
echo         Zum Beenden: Strg+C
echo.
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

endlocal
