@echo off
cd /d %~dp0..
rem Prefer the project venv so a double click works without activating it
set "PY=python"
if exist .venv\Scripts\python.exe set "PY=.venv\Scripts\python.exe"
rem Single source of truth for the version: bowtally\__version__.py
"%PY%" -c "from bowtally.__version__ import __version__ as v; print(v)" > "%TEMP%\bowtally_version.txt"
if errorlevel 1 goto :fail
set /p VERSION=<"%TEMP%\bowtally_version.txt"
"%PY%" -m PyInstaller build\bowtally.spec --noconfirm --distpath build\dist --workpath build\work
if errorlevel 1 goto :fail
set "MAKENSIS=makensis"
where makensis >nul 2>nul || set "MAKENSIS=%ProgramFiles(x86)%\NSIS\makensis.exe"
"%MAKENSIS%" /V2 /DVERSION=%VERSION% build\setup.nsi
if errorlevel 1 goto :fail
rem checksums.txt for the GitHub release: "<sha256>  <installer name>", the format the update check reads
"%PY%" -c "import sys; from pathlib import Path; from bowtally.updater.update_service import sha256_of; p = Path(sys.argv[1]); Path('build/dist/checksums.txt').write_text(f'{sha256_of(p)}  {p.name}\n', encoding='ascii')" "build\dist\BowTally-%VERSION%-Setup.exe"
if errorlevel 1 goto :fail
echo Build %VERSION% abgeschlossen. App, Installer und checksums.txt liegen in build\dist
pause
exit /b 0
:fail
echo Build fehlgeschlagen.
pause
exit /b 1
