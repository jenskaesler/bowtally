@echo off
cd /d %~dp0..
python -m PyInstaller build\bowtally.spec --noconfirm --distpath build\dist --workpath build\work
echo Build abgeschlossen.
pause
