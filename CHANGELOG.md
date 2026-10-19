# Changelog

Alle nennenswerten Änderungen an BowTally. Format nach
[Keep a Changelog](https://keepachangelog.com/de/1.1.0/), Versionierung nach
[Semantic Versioning](https://semver.org/lang/de/).

## [Unveröffentlicht]

## [0.5.0] – 2026-10-19

### Hinzugefügt

- **Vereinsprofil erweitert**: Bankdaten (Kontoinhaber, IBAN, BIC, Verwendungszweck-Vorlage) und
  Parcour-Beschreibung als neue Felder im Vereinsprofil hinterlegbar.
- **Einstellungen neu strukturiert**: Fünf Tabs – Vereinsprofil (mit gruppierten Abschnitten),
  Bankdaten, Design, Verhalten, Druck. Das Vereinsprofil ist in Gruppen (Verein, Adresse, Kontakt,
  Parcour-Beschreibung, Notizen, Logo) mit Scroll-Bereich gegliedert.
- **Vereinsname im Fenstertitel**: Die Titelleiste zeigt „BowTally – [Vereinsname]", sofern ein
  Vereinsname hinterlegt ist.
- **Vereinslogo auf beiden Dashboards**: Das Logo erscheint oben rechts im globalen Dashboard und
  im Turnier-Dashboard.
- **Dashboard-Erweiterungen**: Aktive Turniere zeigen die Auslastung als `(angemeldet/max)`.
  Die Schützen-Kachel zeigt die Anzahl der Schützen ohne Vereinszugehörigkeit.
- **Turnier-Assistent verbessert**:
  - Reiter 1 (Stammdaten): Veranstalter und Ort per Knopf aus dem Vereinsprofil übernehmen.
  - Reiter 2 (Regelwerk): Redesign mit formatierter Regelwerksbeschreibung als Karte rechts.
  - Reiter 3 (Bogenklassen): Standardmäßig keine Klasse vorausgewählt; neuer „Eigene"-Knopf
    wählt alle benutzerdefinierten Bogenklassen aus.
  - Reiter 4 (Konfiguration): Parcour-Beschreibung per Knopf aus den Stammdaten übernehmen.
  - Reiter 7 (Kontakt & Bank): Alle Bankdaten (IBAN, BIC, Kontoinhaber, Verwendungszweck) aus
    dem Vereinsprofil importierbar.
  - Reiter 9 (Zusammenfassung): Trennlinien zwischen Abschnitten, einheitlicher Einzug (140 px
    feste Breite für Beschriftungen), grau dargestellte Labels für bessere Lesbarkeit.
- **Leitfaden-Direktlinks**: Die drei „Turnier bearbeiten"-Knöpfe in den Phasen navigieren jetzt
  direkt zur zugehörigen Assistentenseite (Grunddaten, Kontaktdaten, Bankdaten, Bogenklassen)
  und tragen aussagekräftige Beschriftungen.

## [0.4.0] – 2026-10-19

### Hinzugefügt

- **Turnierphasen**: Ausschreibung, Vorbereitung, Anmeldung, Einschreibung, Schießen,
  Auswertung, Abgeschlossen. Vor jedem Wechsel werden Voraussetzungen geprüft: Blocker sperren
  den Wechsel, Warnungen können bewusst übergangen werden. Jeder Wechsel landet im
  Phasenwechsel-Protokoll.
- **Turnier-Kontext**: Ein geöffnetes Turnier erscheint oben in der Seitenleiste mit Phasenliste,
  Knopf „Nächste Phase“ und Protokoll. Es wird beim nächsten Start wiederhergestellt.
- **Leitfaden** je Phase mit Erklärung, Aufgaben und Direktlinks, Statusampeln und abhakbarer
  Checkliste (inklusive Notizen zur Helfereinteilung und Nachbesprechung).
- **Ausschreibungs-PDF** aus den Turnierdaten und Textvorlagen der Einstellungen. BowTally merkt
  sich die erste und die letzte Erstellung und zeigt „Ausschreibung veraltet“, wenn sich die Daten
  danach geändert haben.
- **Startgebühren** je Turnier, vorbelegt aus Vorlagen. Eigene Ansicht zum Bearbeiten.
  Zugewiesene Gebühren können nicht gelöscht werden.
- **Anmelde- und Zahlungsstatus** je Teilnehmer, mit Status-Chips, Schnellaktionen im
  Rechtsklick-Menü und Sammelaktionen („N Anmeldungen bestätigen“, „N Zahlungen als eingegangen
  markieren“).
- **Maximale Teilnehmerzahl** mit Auslastungsbalken. Volle Turniere sperren Zuweisen, Import und
  Walk-ins.
- **Einschreibe-Ansicht** für den Turniertag: Suche nach Name oder Startnummer, Einchecken per
  Enter, Warnung bei offener Zahlung, Walk-in-Erfassung.
- **Einschreibeliste** als PDF zum Ausdrucken.
- **Turnier-Dashboard** mit Teilnehmern, Einnahmen, Ergebnisfortschritt, aktueller Phase und
  nächster Aufgabe, Klassenübersicht und Zeitplan. Das globale Dashboard zeigt einen Countdown bis
  zum nächsten Turnier.
- **Turnier-Assistent** um vier Schritte erweitert: Fristen und Zeiten, Startgebühren, Kontakt
  und Bankdaten (übernehmbar aus dem Vereinsprofil), Hinweise und Texte. Optional wird die
  Ausschreibung direkt nach dem Speichern erstellt.
- **Export aller Turnierdaten**: Teilnehmer, Ergebnisse, Rangliste und Gebühren in einer Datei.
- Filter „Nur unvollständige“ in der Ergebniseingabe.
- Neue Einstellungen: Textvorlagen für die Ausschreibung und das Logo am Ende der Ausschreibung.

### Geändert

- Die Phase ersetzt den bisherigen Status Entwurf/Aktiv/Abgeschlossen. Bestehende Turniere werden
  bei der Migration übernommen (Entwurf → Ausschreibung, Aktiv → Schießen, Abgeschlossen →
  Abgeschlossen).
- Die Ergebnisliste ist ab der Phase „Schießen“ verfügbar.
- Die Seitenleiste ist breiter, „Einstellungen“ steht unten.
- Der Import von Teilnehmerlisten prüft vorab die freien Plätze.

### Behoben

- Beim Walk-in wurde der Check-in-Status durch ein Neuladen des Datensatzes wieder überschrieben.

## [0.3.0] – 2026-10-19

### Hinzugefügt

- **Komponentenbibliothek**: Seitenpanel, Hinweise unten rechts (Toasts), Status-Chips,
  Aktionsleiste, Leerzustände, Bestätigungsdialog, Suchfeld mit Verzögerung, Formularfelder mit
  Prüfung direkt am Feld, Datentabelle.
- Formulare für Schützen, Bogenklassen und Regelwerke im **Seitenpanel** statt in Dialogen, mit
  Rückfrage bei ungespeicherten Änderungen.
- **Ergebniseingabe per Tastatur**: Enter/↓/↑/Tab, Zonenliste beim Bearbeiten, eingefrorene
  Namens- und Summenspalten, Farbmarkierung für Top-Treffer und Fehlschüsse, Klassen- und
  Gruppenfilter, Scheibe für alle Teilnehmer setzen.
- **Teilnehmerverwaltung**: Schützen-Auswahl mit Mehrfachauswahl, Bearbeitung direkt in der
  Tabelle, Sammelaktionen für Klasse und Gruppe.
- **Auswertung**: Podium in Gold/Silber/Bronze, „ex aequo“ bei Gleichstand, PDF-Erstellung im
  Hintergrund, Export als Auswahlmenü.
- **Dashboard** mit Karten und „Letzte Aktivität“.
- Turnier-Assistent mit Fortschrittsanzeige, Klassen-Chips und Bearbeiten-Sprüngen in der
  Zusammenfassung.
- Globale Tastenkürzel (`Strg+N`, `Strg+F`, `Strg+S`, `F5`, `F1`) und Übersicht über das
  Hilfe-Symbol in der Statusleiste.
- Schützen können gelöscht werden, sofern sie an keinem Turnier teilgenommen haben.

### Geändert

- Nicht-kritische Meldungen erscheinen als Hinweis statt als Meldungsfenster.
- Löschen und andere unumkehrbare Aktionen fragen immer über einen Bestätigungsdialog nach.

### Behoben

- „(keine)“ als Standardklasse verhinderte das Speichern eines Schützen.
- Tabellen waren anfangs absteigend nach der ersten Spalte sortiert.
- Farbige Zellen in Ergebniseingabe und Rangliste wurden vom Stylesheet überdeckt.
- Nach Enter in der Ergebniseingabe ging das nächste getippte Zeichen verloren.
- Esc bei offener Zonenliste verschob den Fokus ins Suchfeld.

## [0.2.0] – 2026-10-18

### Hinzugefügt

- **Dunkler Modus**: hell, dunkel oder wie Windows, umschaltbar in der Seitenleiste und in den
  Einstellungen. Die dunklen Farben sind eigene, änderbare Einstellungen.
- Farbige Statusanzeige für Turniere im Turnierkopf und auf dem Dashboard.

### Geändert

- Überarbeitetes Erscheinungsbild: neutrale Seitenleiste mit eigenen Linien-Icons, flache
  Tabellen, unterstrichene Reiter, abgerundete Eingabefelder und Knöpfe.
- Installer mit **NSIS** statt Inno Setup. `build\build.bat` baut Anwendung und Installer in
  einem Schritt und verwendet automatisch das Projekt-venv.
- Die Version wird nur noch in `bowtally/__version__.py` gepflegt.

## [0.1.0] – 2026-10-18

### Hinzugefügt

- Erste Version: Schützen-Stammdaten, Regelwerke (IBO 3D, ASA 3D, WA 3D), Bogenklassen,
  Turnier-Assistent, Teilnehmerverwaltung, Ergebniseingabe, Ranglisten mit Tie-Break,
  druckfertige Ergebnisliste als PDF, Import/Export CSV/XLSX/ODS, Einstellungen mit Vereinsprofil
  und Farbschema.
- SQLite-Datenbank mit Alembic-Migrationen, Build mit PyInstaller.

[Unveröffentlicht]: https://github.com/jenskaesler/bowtally/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/jenskaesler/bowtally/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/jenskaesler/bowtally/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/jenskaesler/bowtally/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/jenskaesler/bowtally/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/jenskaesler/bowtally/releases/tag/v0.1.0
