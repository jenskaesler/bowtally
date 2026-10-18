# BowTally

**BowTally** ist eine Desktop-Anwendung zur Verwaltung und Auswertung von 3D-Bogenturnieren.
Sie ist für Bogenvereine gedacht und ohne Anpassungen nutzbar: Regelwerke, Bogenklassen,
Farben, Druckeinstellungen und Vereinsdaten sind vollständig in der Anwendung konfigurierbar.

![Screenshot](docs/screenshot.png)
<!-- Screenshot-Platzhalter: docs/screenshot.png -->

## Features

- **Dashboard** mit aktiven Turnieren, nächstem Turnier, Schützen/Vereinen und letzter Aktivität
- **Schützen-Stammdaten** mit Suche, Status (aktiv/inaktiv), Löschen bzw. Deaktivieren, Import
  (CSV/XLSX/ODS mit Spalten-Mapping, Vorschau, Validierung und Duplikat-Strategie) und Export
- **Regelwerke** (IBO 3D, ASA 3D, WA 3D eingebaut) – schreibgeschützt, klonbar, Zonen-Editor mit
  Drag-and-Drop
- **Bogenklassen** – zehn Standardklassen, klonbar, Reihenfolge per Drag-and-Drop
- **Turnier-Wizard** in fünf Schritten mit Fortschrittsanzeige und Bearbeiten-Sprüngen
- **Teilnehmerverwaltung** mit Schützen-Auswahl, Inline-Bearbeitung von Klasse/Gruppe,
  Sammelaktionen, automatischer Startnummernvergabe und Listen-Import
- **Ergebniseingabe** komplett per Tastatur (Zahl oder Zone, Enter/↓/↑/Tab), eingefrorene Namens-
  und Summenspalten, Farbmarkierung für Top-Treffer und Fehlschüsse, Klassen- und Gruppenfilter,
  sofortiges Speichern
- **Status-Workflow** Entwurf → Aktiv → Abgeschlossen (abgeschlossene Turniere sind gesperrt)
- **Ranglisten** je Bogenklasse und gesamt, Podium hervorgehoben, „ex aequo“ bei Gleichstand,
  konfigurierbarer Tie-Break, Export CSV/XLSX/ODS
- **Druckfertige Ergebnisliste** als PDF (Deckblatt mit Vereinslogo, eine Seite je Klasse)
- **Bedienung**: Seitenpanel statt Dialoge, Inline-Validierung, Benachrichtigungen, Tastenkürzel
  (Strg+N/F/S, F5, F1 für die Übersicht)
- **Theming**: Hell, Dunkel oder wie Windows; alle Farben und die Schriftart sind änderbar

## Anforderungen

- Windows 10 oder 11
- Für Endnutzer ist **keine Python-Installation nötig** – der Installer bringt alles mit.

## Installation

1. Aktuellen Installer `BowTally-<version>-Setup.exe` von der
   [Releases-Seite](https://github.com/jenskaesler/bowtally/releases) herunterladen.
2. Installer ausführen und den Anweisungen folgen.

Die Datenbank liegt unter `%APPDATA%\BowTally\bowtally.db`, das Log unter
`%APPDATA%\BowTally\app.log`. Beide bleiben bei Deinstallation und Updates erhalten.
Zur Datensicherung genügt eine Kopie von `bowtally.db`.

## Entwicklung

```bash
git clone https://github.com/jenskaesler/bowtally.git
cd bowtally
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
python -m bowtally.main        # oder: bowtally
pytest                         # Tests
```

Für Tests oder portable Nutzung kann das Datenverzeichnis per Umgebungsvariable
`BOWTALLY_DATA_DIR` umgelenkt werden.

### Datenbank-Migrationen

Das Schema wird mit Alembic verwaltet (`bowtally/database/migrations`). Beim Start wird die
Datenbank automatisch auf den neuesten Stand gebracht. Neue Migration anlegen:

```bash
cd bowtally/database
alembic -c alembic.ini revision -m "beschreibung"
```

Neue Einstellungen werden per Migration in `app_settings` eingefügt und erscheinen automatisch
im Einstellungsdialog (Tab „Druck und Verhalten“).

### Projektstruktur

```
bowtally/
  database/   ORM-Modelle, Engine, Alembic-Migrationen, Seed-Daten
  services/   Geschäftslogik (kein UI-Code)
  ui/         PySide6-Oberfläche (Views, Dialoge, Widgets, Theme)
  reports/    PDF-Ergebnisliste (reportlab)
  io/         Import/Export CSV, XLSX, ODS
build/        PyInstaller-Spec, Build-Skript, NSIS-Skript
```

## Build

1. **Anwendung bauen** (PyInstaller, onedir):
   ```bat
   build\build.bat
   ```
   Ergebnis: `build\dist\BowTally\BowTally.exe`
2. **Installer erstellen** mit [NSIS 3](https://nsis.sourceforge.io/):
   ```bat
   "C:\Program Files (x86)\NSIS\makensis.exe" build\setup.nsi
   ```
   Ergebnis: `build\dist\BowTally-<version>-Setup.exe`
   (andere Version: `makensis /DVERSION=0.2.0 build\setup.nsi`)

## Git-Remote

Das Repository wird lokal ohne Remote initialisiert. Remote manuell hinzufügen:

```bash
git remote add origin https://github.com/jenskaesler/bowtally.git
git push -u origin main
```

## Lizenz

BowTally ist freie Software unter der **GNU General Public License v3.0** – siehe [LICENSE](LICENSE).
