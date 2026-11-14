@echo off
rem Einmaliges Setup der Entwicklungsumgebung fuer BowTally.
rem Ausfuehren nach dem ersten Clone oder wenn das venv fehlt.
cd /d %~dp0..

echo.
echo === BowTally Dev-Setup ===
echo.

rem Pruefen ob Python erreichbar ist
python --version >nul 2>nul
if errorlevel 1 (
    echo FEHLER: Python nicht gefunden. Bitte Python 3.11+ installieren und im PATH eintragen.
    pause
    exit /b 1
)

rem Venv anlegen falls nicht vorhanden
if not exist .venv\Scripts\python.exe (
    echo Lege .venv an...
    python -m venv .venv
    if errorlevel 1 goto :fail
) else (
    echo .venv bereits vorhanden, wird wiederverwendet.
)

echo Installiere Abhaengigkeiten inkl. Dev-Tools...
.venv\Scripts\pip install --upgrade pip --quiet
.venv\Scripts\pip install -e ".[dev]" --quiet
if errorlevel 1 goto :fail

echo.
echo Fertig. Venv liegt unter .venv\
echo Zum Bauen: build\build.bat
echo.
pause
exit /b 0

:fail
echo.
echo Setup fehlgeschlagen.
pause
exit /b 1
