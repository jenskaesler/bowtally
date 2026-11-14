# 🏹 BowTally

> Turnierverwaltung für 3D-Bogenturniere – von der Ausschreibung bis zur druckfertigen Ergebnisliste.

[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D6?logo=windows&logoColor=white)](https://www.microsoft.com/windows)
[![Language](https://img.shields.io/badge/Language-Python%203.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-NC--Copyleft-orange)](LICENSE)
[![Version](https://img.shields.io/badge/Version-2026.11.2-blue)](CHANGELOG.md)

---

## 🤔 Wofür?

Bogenvereine organisieren 3D-Turniere bislang mit einer Mischung aus Tabellenkalkulation, Word-Vorlagen und handgeschriebenen Listen. BowTally ersetzt das komplett: ein einziges Programm führt durch alle acht Phasen eines Turniers – von der Ausschreibung bis zur Siegerehrung.

Die Anwendung läuft vollständig offline. Alle Daten bleiben lokal auf dem Gerät. Es werden keine personenbezogenen Daten oder Turnierdaten an externe Server übertragen. Der optionale Nextcloud-Sync überträgt Daten ausschließlich auf expliziten Nutzerwunsch an einen selbst betriebenen Server. Weitere Hinweise unter [docs/PRIVACY.md](docs/PRIVACY.md).

---

## 🔄 Turnierphasen

```mermaid
flowchart LR
    A([🖊️ <br> Entwurf]) --> B([📄 <br> Ausschreibung])
    B --> C([🔧 <br> Vorbereitung])
    C --> D([✅ <br> Anmeldung])
    D --> E([🏁 <br> Einschreibung])
    E --> F([🎯 <br> Schießen])
    F --> G([🏆 <br> Auswertung])
    G --> H([✔️ <br> Abgeschlossen])

    style A fill:#6c757d,color:#fff,stroke:none
    style B fill:#0d6efd,color:#fff,stroke:none
    style C fill:#0dcaf0,color:#000,stroke:none
    style D fill:#198754,color:#fff,stroke:none
    style E fill:#20c997,color:#fff,stroke:none
    style F fill:#ffc107,color:#000,stroke:none
    style G fill:#fd7e14,color:#fff,stroke:none
    style H fill:#343a40,color:#fff,stroke:none
```

---

## ✨ Funktionen

### Turnierablauf

- 🔄 **Acht Phasen** – geführter Ablauf: Entwurf → Ausschreibung → Vorbereitung → Anmeldung → Einschreibung → Schießen → Auswertung → Abgeschlossen. Vor jedem Wechsel prüft BowTally Voraussetzungen: Blocker sperren den Wechsel, Warnungen können bewusst übergangen werden. Jeder Wechsel wird protokolliert.
- 📋 **Leitfaden** – Erklärung, Aufgaben mit Direktlinks, Statusampeln und abhakbare Checkliste je Phase.
- 🧙 **Turnier-Assistent** – neun Schritte: Grunddaten, Regelwerk, Bogenklassen, Parcours, Fristen und Zeiten, Startgebühren, Kontakt und Bankdaten, Texte, Zusammenfassung.
- 📋 **Turnier kopieren** – bestehendes Turnier als Vorlage nutzen; Parcours-Ziele und Preise werden übernommen, Teilnehmer und Ergebnisse nicht.
- 📅 **Jahreskalender** – Monatsraster mit allen Turnieren als farbige Badges nach Phase, ICS-Export.

### Ausschreibung und Anmeldung

- 📄 **Ausschreibungs-PDF** – Termin, Ablauf, Klassen, Startgeld, Bankverbindung und Kontakt aus den Turnierdaten; BowTally zeigt an, wenn die Ausschreibung nach Änderungen veraltet ist.
- 💶 **Startgebühren** – je Turnier, vorbelegt aus Vorlagen; Einnahmenübersicht mit erwarteten, eingegangenen und ausstehenden Beträgen.
- ✅ **Anmelde- und Zahlungsstatus** – je Teilnehmer; Schnellaktionen per Rechtsklick und Aktionsleiste.
- 🔢 **Maximale Teilnehmerzahl** – Auslastungsbalken; bei voller Belegung sind Zuweisen, Import und Walk-ins gesperrt.

### Turniertag

- 🏁 **Einschreibe-Ansicht** – Suche nach Name oder Startnummer, Einchecken per Enter, Walk-in-Erfassung, Einschreibeliste drucken.
- ⌨️ **Ergebniseingabe per Tastatur** – Enter/↓/↑ wechselt Teilnehmer, Tab die Scheibe; Name und Summe bleiben beim Scrollen sichtbar; jede Eingabe wird sofort gespeichert.
- 🎯 **Auslosung** – automatische Gruppeneinteilung mit Startnummer und Startscheibe, optional getrennt nach Bogenklasse; direkt danach Wertungszettel drucken.
- 🗓️ **Zeitplan** – Startgruppen mit Startzeit und Dauer, PDF-Druck Zeitplan-Aushang.
- 📐 **Parcours-Planung** – alle Scheiben/Ziele mit Distanz, Pfeilstopp, Geländetyp, Reihenfolge per Drag-and-Drop; PDF-Druck Aufbauplan und Scheibenplan.
- 📋 **Wertungszettel-Vorlagen** – konfigurierbare Spalten per Drag-and-Drop-Editor; vier eingebaute Vorlagen: 3D-Standard, Feld-Standard, Halle 10-Ring, Blasrohr-Standard.

### Auswertung

- 🏆 **Ranglisten** – je Bogenklasse und gesamt, Podium hervorgehoben, „ex aequo" bei Gleichstand, einstellbarer Tie-Break.
- 📄 **Ergebnisliste** – druckfertiges PDF mit Deckblatt und Vereinslogo, eine Seite je Klasse.
- 🥇 **Preis- und Siegerliste** – Rangliste mit zugewiesenen Preisen je Klasse als PDF.
- 📜 **Urkunden** – eine Seite je Podiumsplatz mit konfigurierbaren Platzhaltern (`{name}`, `{klasse}`, `{platz}`, `{punkte}`, `{turniername}`, `{datum}`) als PDF.
- 📤 **Export** – CSV, Excel oder OpenDocument, auch alle Turnierdaten auf einmal.
- 🔁 **Multi-Runden-Turniere** – beliebig viele Runden, jede mit eigenem Regelwerk; Wertung je Scheibe, je Runde oder als Gesamtwertung.

### Stammdaten

- 🏹 **Schützen** – Suche, aktiv/inaktiv; Import CSV/XLSX/ODS mit Spalten-Zuordnung, Vorschau, Validierung und Duplikatbehandlung.
- 📏 **Regelwerke** – 14 eingebaute Regelwerke (IBO 3D, ASA 3D, WA 3D, DBSV Wald-/Jagdrunde, IFAA Feld bekannt/unbekannt, WA Halle 18 m/25 m, 3D Hunter, NFAA 3D u. a.) plus eigene durch Klonen mit Zonen-Editor.
- 🎯 **Bogenklassen** – zehn Standardklassen, eigene Klassen, Reihenfolge per Drag-and-Drop.

### Einstellungen

- 🏢 **Vereinsprofil** – Name, Adresse, Logo, Bankdaten (IBAN, BIC, Verwendungszweck-Vorlage mit Platzhaltern).
- 👥 **Vereinsvorstand** – Vorname, Nachname, Telefon und E-Mail je Vorstandsrolle; im Turnier-Assistenten per Klick als Turnierkontakt übernehmen.
- 🎨 **Design** – Hell/Dunkel/System-Theme, Primärfarbe und alle App-Farben individuell anpassbar, Schriftart wählbar.
- 💾 **Backup** – lokales ZIP-Backup, Nextcloud-Upload (WebDAV), automatisches Backup beim Beenden, Wiederherstellung aus Datei.

---

## 📋 Anforderungen

| Komponente | Version |
|---|---|
| Windows | 10 oder 11 (64 Bit) |
| Python | 3.11 oder neuer (nur für Entwicklung) |
| NSIS | 3.x (nur für Build) |

Für Endanwender ist **keine Python-Installation nötig** – der Installer bringt alles mit.

---

## 🏗️ Projektstruktur

```
bowtally/
│
├── bowtally/
│   ├── __version__.py          – Versionsnummer (einzige Quelle der Wahrheit)
│   ├── database/               – ORM-Modelle, Engine, Alembic-Migrationen, Seed-Daten
│   ├── services/               – Geschäftslogik (kein UI-Code): Turniere, Teilnehmer,
│   │                             Wertung, Rangliste, Parcours, Auslosung, Preise, Einstellungen
│   ├── reports/                – PDF-Erzeugung: Ergebnisliste, Ausschreibung, Einschreibeliste,
│   │                             Parcours, Zeitplan, Wertungszettel, Urkunden, Preis-/Siegerliste
│   ├── io/                     – Import/Export CSV, XLSX, ODS
│   └── ui/
│       ├── components/         – Wiederverwendbare Widgets (Seitenpanel, Tabelle, Chips, …)
│       ├── views/              – Seiten (Dashboard, Leitfaden, Turniere, Schützen, …)
│       ├── dialogs/            – Turnier-Assistent, Auslosung, Einstellungen, Import/Export
│       └── theme.py            – Stylesheet, Farbpalette und Icons aus den Einstellungen
│
├── build/
│   ├── bowtally.spec           – PyInstaller-Spec
│   ├── build.bat               – Baut Anwendung (PyInstaller) und Installer (NSIS) in einem Schritt
│   ├── setup-dev.bat           – Einmaliges Dev-Setup: venv anlegen und Abhängigkeiten installieren
│   └── setup.nsi               – NSIS-Installer-Skript
│
├── docs/
│   ├── BowTally_Ersteinrichtung.md – Benutzeranleitung: Installation und Ersteinrichtung
│   ├── BowTally_Phasensystem.md    – Benutzeranleitung: Turnierphasen Schritt für Schritt
│   ├── PRIVACY.md                  – Datenschutzhinweise
│   ├── SECURITY.md                 – Sicherheitshinweise und Disclosure Policy
│   └── THIRD-PARTY-NOTICES.md      – Drittanbieter-Lizenzen
│
├── tests/                      – pytest
├── CHANGELOG.md
├── LICENSE
└── README.md
```

---

## ⚡ Schnellstart

### 1. Installieren

Installer `BowTally-<version>-Setup.exe` von der [Releases-Seite](https://github.com/jenskaesler/bowtally/releases) herunterladen und ausführen.

### 2. Einrichten

Beim ersten Start erscheint der Erststart-Assistent. Anschließend unter **Einstellungen → Vereinsprofil** Vereinsname, Kontakt und Logo eintragen.

### 3. Erstes Turnier anlegen

**Turniere → Neues Turnier** – den Assistenten durchgehen; am Ende „Ausschreibung jetzt generieren" angehakt lassen.

### 4. Phasen durchlaufen

Im **Leitfaden** die Aufgaben je Phase abarbeiten und über **Nächste Phase** in der Seitenleiste weiterschalten.

### 5. Turniertag

In der **Einschreibung** einchecken, im **Schießen** Ergebnisse eintragen.

### 6. Auswertung

Ergebnisliste, Urkunden und Preis- und Siegerliste erstellen, Turnier abschließen.

---

## 📚 Dokumentation

| Dokument | Inhalt |
|---|---|
| [Ersteinrichtung](docs/BowTally_Ersteinrichtung.md) | Installation, Stammdaten, erstes Turnier anlegen |
| [Phasensystem](docs/BowTally_Phasensystem.md) | Turnierverwaltung Schritt für Schritt – alle acht Phasen erklärt |
| [Datenschutz](docs/PRIVACY.md) | Datenverarbeitung, Speicherorte, optionaler Nextcloud-Sync |
| [Sicherheitshinweise](docs/SECURITY.md) | Schwachstellen melden, Kontakt, Disclosure Policy |
| [Drittanbieter-Lizenzen](docs/THIRD-PARTY-NOTICES.md) | Verwendete Open-Source-Bibliotheken und ihre Lizenzen |

---

## 🔧 Entwicklung

```bat
git clone https://github.com/jenskaesler/bowtally.git
cd bowtally
build\setup-dev.bat
```

`setup-dev.bat` legt `.venv` an und installiert alle Abhängigkeiten inkl. Dev-Tools (`pytest`, `pyinstaller`).

```bat
.venv\Scripts\activate
python -m bowtally.main
pytest
```

Mit der Umgebungsvariable `BOWTALLY_DATA_DIR` lässt sich das Datenverzeichnis umlenken (Tests, portable Installation).

### Datenbank-Migrationen

Schema-Verwaltung mit Alembic (`bowtally/database/migrations`). Beim Start wird die Datenbank automatisch migriert. Neue Migration anlegen:

```bat
cd bowtally\database
alembic -c alembic.ini revision -m "beschreibung"
```

### Datenspeicherorte

| Datei | Ort |
|---|---|
| Datenbank | `%APPDATA%\BowTally\bowtally.db` |
| Log | `%APPDATA%\BowTally\app.log` |
| Erzeugte PDFs | `%TEMP%\BowTally\` |

Datenbank und Log bleiben bei Updates und Deinstallation erhalten. Zur Datensicherung genügt eine Kopie von `bowtally.db`.

---

## 🏭 Build

Voraussetzungen: Dev-venv (siehe oben) und [NSIS 3](https://nsis.sourceforge.io/).

```bat
build\build.bat
```

Das Skript baut mit PyInstaller und danach den Installer mit NSIS. Die Version kommt aus `bowtally/__version__.py`.

| Ergebnis | Ort |
|---|---|
| Anwendung | `build\dist\BowTally\BowTally.exe` |
| Installer | `build\dist\BowTally-<version>-Setup.exe` |

Nur den Installer neu bauen:

```bat
makensis /DVERSION=2026.11.2 build\setup.nsi
```

### Release

1. `.\bump-version.ps1` ausführen und neue Version wählen (oder `-Patch` / `-Month` / `-Version "..."` übergeben).
2. `CHANGELOG.md` ergänzen.
3. `build\build.bat` ausführen.
4. Committen und taggen: `git tag v<version>`, dann `git push origin main --tags`.

---

## 📜 Lizenz

BowTally steht unter einer eigenen **Nicht-Kommerziellen Copyleft-Lizenz**, siehe [LICENSE](LICENSE).

- **Keine kommerzielle Nutzung** ohne ausdrückliche schriftliche Genehmigung.
- **Copyleft**: Änderungen am Quellcode müssen öffentlich auf GitHub veröffentlicht werden.

Lizenzanfragen: [mail@jens-kaesler.de](mailto:mail@jens-kaesler.de)
