# BowTally

**BowTally** ist eine Windows-Desktop-Anwendung für 3D-Bogenturniere: von der Ausschreibung über
Anmeldung, Einschreibung und Ergebniseingabe bis zur druckfertigen Ergebnisliste.

Die Anwendung ist für Bogenvereine gedacht und ohne Anpassungen nutzbar. Regelwerke,
Bogenklassen, Startgebühren, Texte, Farben, Druckeinstellungen und Vereinsdaten werden in der
Anwendung gepflegt.

![Screenshot](docs/screenshot.png)
<!-- Screenshot-Platzhalter: docs/screenshot.png -->

Aktuelle Version: **0.4.0** – Änderungen siehe [CHANGELOG](CHANGELOG.md).

## Funktionen

### Turnierablauf

- **Sieben Phasen** mit geführtem Ablauf: Ausschreibung → Vorbereitung → Anmeldung →
  Einschreibung → Schießen → Auswertung → Abgeschlossen.
  Vor jedem Phasenwechsel prüft BowTally die Voraussetzungen. Fehlt etwas Zwingendes, ist der
  Wechsel gesperrt. Offene Punkte werden als Warnung angezeigt und können bewusst übergangen
  werden. Jeder Wechsel wird protokolliert.
- **Aktives Turnier in der Seitenleiste**: Phasenübersicht mit Datum, Knopf „Nächste Phase“ und
  Phasenwechsel-Protokoll. Das zuletzt geöffnete Turnier wird beim Start wiederhergestellt.
- **Leitfaden** je Phase: Erklärung, Aufgaben mit Direktlinks, Statusampeln für den nächsten
  Phasenwechsel und eine abhakbare Checkliste (Parcours, Helfer, Einschreibetisch,
  Siegerehrung, Aushang).
- **Turnier-Assistent** in neun Schritten: Grunddaten, Regelwerk, Bogenklassen, Parcours,
  Fristen und Zeiten, Startgebühren, Kontakt und Bankdaten, Texte, Zusammenfassung.

### Ausschreibung und Anmeldung

- **Ausschreibungs-PDF** aus den Turnierdaten: Termin und Ablauf, Parcours und Wertung, Klassen,
  Startgeld, Bankverbindung mit Verwendungszweck, Kontakt und Hinweise. BowTally zeigt an, wenn
  die Ausschreibung nach Änderungen veraltet ist.
- **Startgebühren** je Turnier, vorbelegt aus Vorlagen.
- **Anmeldestatus** je Teilnehmer: gemeldet, bestätigt, eingecheckt, nicht gestartet,
  abgebrochen, disqualifiziert, zurückgezogen.
- **Zahlungsstatus** je Teilnehmer: ausstehend, erwartet, bezahlt (mit Betrag und Datum).
- **Maximale Teilnehmerzahl** mit Auslastungsbalken. Bei voller Belegung sind Zuweisen, Import
  und Walk-ins gesperrt.
- **Einnahmenübersicht**: erwartete, eingegangene und ausstehende Beträge je Gebühr.

### Turniertag

- **Einschreibe-Ansicht**: Name oder Startnummer eingeben, mit Enter einchecken, Warnung bei
  offener Zahlung, Walk-ins direkt erfassen, Einschreibeliste drucken.
- **Ergebniseingabe** komplett per Tastatur: Zahl tippen oder Zone wählen, Enter/↓/↑ wechselt
  den Teilnehmer, Tab die Scheibe. Name und Summe bleiben beim Scrollen sichtbar. Top-Treffer und
  Fehlschüsse sind farbig markiert. Jede Eingabe wird sofort gespeichert.
- **Filter** nach Klasse, Startgruppe und „nur unvollständige“; eine Scheibe lässt sich für alle
  Teilnehmer auf einmal setzen.

### Auswertung

- **Ranglisten** je Bogenklasse und gesamt, Podium hervorgehoben, „ex aequo“ bei Gleichstand,
  einstellbarer Tie-Break.
- **Druckfertige Ergebnisliste** als PDF: Deckblatt mit Vereinslogo, eine Seite je Klasse.
- **Export** als CSV, Excel oder OpenDocument, auch alle Turnierdaten auf einmal.
- **Turnier-Dashboard**: Teilnehmer, Einnahmen, Ergebnisfortschritt, Klassen, Zeitplan und die
  nächste offene Aufgabe.

### Stammdaten

- **Schützen** mit Suche, aktiv/inaktiv, Import aus CSV/XLSX/ODS (Spalten-Zuordnung, Vorschau,
  Validierung, Umgang mit Duplikaten) und Export.
- **Regelwerke**: IBO 3D, ASA 3D und WA 3D eingebaut und schreibgeschützt; eigene Regelwerke
  durch Klonen, mit Zonen-Editor.
- **Bogenklassen**: zehn Standardklassen, eigene Klassen, Reihenfolge per Drag-and-Drop.

### Bedienung

- Formulare im Seitenpanel mit Prüfung direkt am Feld, Hinweise unten rechts statt
  Meldungsfenster, Aktionsleiste für ausgewählte Zeilen, Rechtsklick-Menüs.
- Tastenkürzel: `Strg+N` Neu, `Strg+F` Suchen, `Strg+S` Speichern, `F5` Neu laden,
  `F1` Übersicht aller Kürzel.
- Darstellung hell, dunkel oder wie Windows. Alle Farben und die Schriftart sind änderbar.

## Schnellstart

1. **Einstellungen → Vereinsprofil**: Vereinsname, Kontakt und Logo eintragen.
2. **Turniere → Neues Turnier**: den Assistenten durchgehen und am Ende
   „Ausschreibung jetzt generieren“ angehakt lassen.
3. Im **Leitfaden** die Aufgaben der Phase abarbeiten und über **Nächste Phase** in der
   Seitenleiste weiterschalten.
4. In der **Anmeldung** Schützen zuweisen oder eine Liste importieren, Anmeldungen bestätigen
   und Zahlungen verbuchen (Rechtsklick oder Aktionsleiste).
5. Am Turniertag in der **Einschreibung** einchecken und während des **Schießens** die
   Ergebnisse eintragen.
6. In der **Auswertung** die Ergebnisliste erstellen und das Turnier abschließen.

## Anforderungen

- Windows 10 oder 11 (64 Bit)
- Für Endnutzer ist **keine Python-Installation nötig**, der Installer bringt alles mit.

## Installation

1. Installer `BowTally-<version>-Setup.exe` von der
   [Releases-Seite](https://github.com/jenskaesler/bowtally/releases) herunterladen.
2. Installer ausführen. Eine Desktop-Verknüpfung ist optional.

Die Daten liegen im Benutzerprofil:

| Datei | Ort |
|---|---|
| Datenbank | `%APPDATA%\BowTally\bowtally.db` |
| Log | `%APPDATA%\BowTally\app.log` |
| Erzeugte PDFs | `%TEMP%\BowTally\` |

Datenbank und Log bleiben bei Updates und bei der Deinstallation erhalten. Beim ersten Start
einer neuen Version wird die Datenbank automatisch auf den neuen Stand gebracht. Zur
Datensicherung genügt eine Kopie von `bowtally.db`.

## Entwicklung

Voraussetzung: Python 3.11 oder neuer.

```bash
git clone https://github.com/jenskaesler/bowtally.git
cd bowtally
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
python -m bowtally.main        # oder: bowtally
pytest                         # Tests
```

Mit der Umgebungsvariable `BOWTALLY_DATA_DIR` lässt sich das Datenverzeichnis umlenken, etwa für
Tests oder eine portable Installation.

### Projektstruktur

```
bowtally/
  database/   ORM-Modelle, Engine, Alembic-Migrationen, Seed-Daten
  services/   Geschäftslogik (kein UI-Code): Turniere, Teilnehmer, Wertung, Rangliste, Einstellungen
  reports/    PDFs: Ergebnisliste, Ausschreibung, Einschreibeliste (reportlab)
  io/         Import/Export CSV, XLSX, ODS
  ui/
    components/  wiederverwendbare Widgets (Seitenpanel, Tabelle, Hinweise, Chips, …)
    views/       Seiten (Dashboard, Leitfaden, Turniere, Teilnehmer, Ergebnisse, …)
    dialogs/     Turnier-Assistent, Einstellungen, Import/Export
    theme.py     Stylesheet, Farbpalette und Icons aus den Einstellungen
build/        PyInstaller-Spec, Build-Skript, NSIS-Skript
tests/        pytest
```

### Datenbank-Migrationen

Das Schema wird mit Alembic verwaltet (`bowtally/database/migrations`). Beim Start wird die
Datenbank automatisch auf den neuesten Stand gebracht. Neue Migration anlegen:

```bash
cd bowtally/database
alembic -c alembic.ini revision -m "beschreibung"
```

Neue Einstellungen werden per Migration in `app_settings` eingefügt und erscheinen automatisch
im Einstellungsdialog.

## Build

Voraussetzungen: das Entwicklungs-venv (siehe oben) und [NSIS 3](https://nsis.sourceforge.io/).

```bat
build\build.bat
```

Das Skript baut die Anwendung mit PyInstaller und danach den Installer mit NSIS. Die Version
kommt aus `bowtally/__version__.py`.

| Ergebnis | Ort |
|---|---|
| Anwendung | `build\dist\BowTally\BowTally.exe` |
| Installer | `build\dist\BowTally-<version>-Setup.exe` |

Nur den Installer neu bauen: `makensis /DVERSION=0.4.0 build\setup.nsi`

### Release

1. Version in `bowtally/__version__.py` anheben und `CHANGELOG.md` ergänzen.
2. `build\build.bat` ausführen.
3. Committen und taggen: `git tag v<version>`, dann `git push origin main --tags`.

## Git-Remote

Das Repository wurde lokal ohne Remote angelegt. Remote hinzufügen:

```bash
git remote add origin https://github.com/jenskaesler/bowtally.git
git push -u origin main --tags
```

## Lizenz

BowTally ist freie Software unter der **GNU General Public License v3.0**, siehe
[LICENSE](LICENSE).
