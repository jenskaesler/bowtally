@echo off
cd /d %~dp0..
rem Prefer the project venv so a double click works without activating it
set "PY=python"
if exist .venv\Scripts\python.exe set "PY=.venv\Scripts\python.exe"
"%PY%" -m PyInstaller build\bowtally.spec --noconfirm --distpath build\dist --workpath build\work
if errorlevel 1 goto :fail
set "MAKENSIS=makensis"
where makensis >nul 2>nul || set "MAKENSIS=%ProgramFiles(x86)%\NSIS\makensis.exe"
"%MAKENSIS%" /V2 build\setup.nsi
if errorlevel 1 goto :fail
echo Build abgeschlossen. App und Installer liegen in build\dist
pause
exit /b 0
:fail
echo Build fehlgeschlagen.
pause
exit /b 1
