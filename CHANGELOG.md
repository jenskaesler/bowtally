# Changelog

Alle nennenswerten Änderungen an BowTally. Format nach
[Keep a Changelog](https://keepachangelog.com/de/1.1.0/), Versionierung nach
dem Schema `yyyy.MM.patch` (Jahr.Monat.Patch).

## [Unveröffentlicht]

## [2026.10.4] – 2026-10-25

### Hinzugefügt

- **Multi-Runden-Turniere**: Turniere können aus mehreren Runden bestehen. Drei Wertungsmodi
  wählbar: je Scheibe (`per_target`), je Runde (`per_round`) oder Gesamtwertung (`total_only`).
  Jede Runde hat eine eigene Bezeichnung, ein eigenes Regelwerk, Scheibenzahl, Pfeile und
  Entfernungstyp.
- **Turnier-Assistent – Konfigurationsseite neu**: Rundenstruktur direkt in einer Tabelle
  pflegen (Bezeichnung, Regelwerk, Scheiben, Pfeile, Entfernung). Zeilen per „+ Runde" ergänzen
  oder per Löschen-Button entfernen. Die separaten Felder „Anzahl Scheiben", „Schüsse je Scheibe"
  und „Anzahl Runden" wurden durch die Tabelle ersetzt.
- **14 integrierte Regelwerke**: Zu den drei eingebauten Regelwerken (IBO 3D, ASA 3D, WA 3D)
  kommen elf weitere: 3D Hunter (IBO), 3D Standard 3-Pfeil, Feldbogen IFAA (bekannte Entfernung),
  Feldbogen IFAA (unbekannte Entfernung), WA Halle 18m (mit X-Ring-Tiebreak), Blasrohr Standard,
  DBSV 3D-Waldrunde, DBSV 3D-Jagdrunde, IBO 3D mit 12-Ring, NFAA 3D und WA Halle 25m.
- **Leitfaden**: Aufgabe „Rundenstruktur konfiguriert" in der Vorbereitungsphase.

### Behoben

- **Nextcloud-Backup**: HTTP 409 (Conflict) beim Erstellen bereits existierender Ordner wird jetzt
  korrekt ignoriert (Nextcloud verhält sich hier abweichend vom WebDAV-Standard, der 405 liefert).

## [2026.10.1] – 2026-10-24

### Verbessert

- **UX: Checkbox-Labels** präziser: „Abgeschlossene Turniere anzeigen" und „Inaktive Schützen anzeigen"
- **Leitfaden → Einnahmen**: Navigiert jetzt direkt zum Turnier-Dashboard statt zur globalen Übersicht
- **Rechtsklick-Menüs**: Tooltips entfernt; Bedingungen im Teilnehmer-Menü präzisiert (Bestätigen nur für Gemeldet/Warteliste, Zahlung nur bei hinterlegter Gebühr, DNS/Zurückziehen nur für aktive Teilnehmer)
- **App-Hilfe**: Umbau von Tab-Widget auf geteilte Ansicht (Liste links, Inhalt rechts); 9 Abschnitte auf 7 zusammengeführt; neuer Abschnitt „Rechtsklick-Menüs"

## [2026.10.0] – 2026-10-24

### Hinzugefügt

- **Vereinsvorstand-Tab**: Eigener Tab in den Einstellungen für alle fünf Vorstandsrollen
  (1./2. Vorsitzende/r, Kassenwart/in, Sportleiter/in, Bogenreferent/in) mit Vorname, Nachname,
  Telefon und E-Mail. Datenbank-Migration 0007 fügt die zehn neuen Spalten hinzu.
- **Übernehmen-Button im Turnier-Assistenten**: Auf der Kontaktseite übernimmt ein Klick auf
  „Übernehmen" Name, Telefon und E-Mail der gewählten Vorstandsrolle direkt in das Formular.
- **Standard-Kontaktperson**: Im Vereinsprofil-Tab wählbar, welche Vorstandsrolle beim Erstellen
  neuer Turniere als Kontakt vorbelegt wird.
- **App-Hilfe** (F1): Dialog mit Inhaltsverzeichnis und neun Abschnitten – Übersicht, Turniere,
  Schützen, Ergebnisse, Regelwerke, Einstellungen, Platzhalter-Referenz, Tastenkürzel,
  Backup. Enthält alle bisherigen Tastenkürzel-Informationen.
- **Splash-Screen** beim Start mit Vereinslogo, App-Name, Version und Fortschrittsbalken; passt
  sich dem hellen und dunklen Systemthema an.
- **Hilfe-Eintrag** in der Seitenleisten-Navigation (neben Einstellungen und Über BowTally).

### Geändert

- **Turnier kopieren** (vorher „Klonen"): Aktion und Tooltip umbenannt.
- **Einstellungsbeschriftungen vereinheitlicht**: Verweisung auf kurze, einheitliche Labels für
  Sprache, Schriftart, Papiergröße, Format, Tie-Break-Logik, Verwendungszweck und die
  Textvorlagen-Gruppe. Alle Formular-Labels auf einheitliche Breite (130 px) ausgerichtet.
- **Wizard Nächste-Phase-Button**: Pfeilzeichen (›) aus dem Label entfernt.
- **Regeldetails-Überschrift** im Turnier-Assistenten wieder sichtbar über der Regelwerksbeschreibung.
- **Hilfe-Symbol in der Statusleiste** öffnet jetzt die App-Hilfe statt das Tastenkürzel-Formular.
- **Theme-Umschalter** aus der Seitenleiste entfernt – Darstellung weiterhin in
  Einstellungen → Design änderbar.
- **Oberes Hilfe-Menü** entfernt; Hilfe ist über F1, Statusleiste und Seitenleiste erreichbar.
- **`<code>`-Hintergrund und Tabellenzeilen** in der App-Hilfe passen sich jetzt dem
  Dark Mode an.

### Entfernt

- **Notizen-Feld** aus dem Vereinsprofil entfernt.
- **Tastenkürzel-Formular** (eigenständiger Dialog): Tastenkürzel sind jetzt in der App-Hilfe
  unter „Tastenkürzel" zu finden.

## [0.7.0] – 2026-10-20

### Hinzugefügt

- **Phase „Entwurf"**: Neue erste Phase vor der Ausschreibung. Neue Turniere starten jetzt im
  Entwurfsstatus, in dem alle Daten frei bearbeitet werden können. Nach dem Wechsel in die
  Einschreibungsphase ist der Turnier-Assistent gesperrt (Button ausgeblendet).
  Datenbank-Migration 0006 fügt die Phase in bestehende Datenbanken ein.
- **Turnier klonen**: Aus dem Aktionsmenü der Turnierliste lässt sich ein bestehendes Turnier als
  Vorlage klonen. Der Assistent startet mit vorausgefüllten Daten; Teilnehmer und Ergebnisse
  werden nicht übernommen.
- **Dashboard-Kachel „Turnierarchiv"**: Neue Kachel in Zeile 1 zeigt die Anzahl
  abgeschlossener Turniere und führt per Klick zur Turnierliste.
- **Automatisches Backup beim Beenden**: Neuer Schalter im Backup-Tab der Einstellungen.
  Beim Schließen der App wird ein lokales ZIP-Backup erstellt, sofern ein Backup-Pfad gesetzt ist.
- **About-Dialog**: Neuer Eintrag „Über BowTally" in der Seitenleiste mit Versionsnummer,
  Kurzbeschreibung, GitHub-Link, Entwicklerinfo und Lizenzhinweis.
- **Lizenz**: Eigene Nicht-Kommerzielle-Copyleft-Lizenz. Kommerzielle Nutzung erfordert
  schriftliche Genehmigung; Änderungen müssen auf GitHub veröffentlicht werden.

### Geändert

- **Dashboard Kacheln neu geordnet**: Zeile 1 zeigt Aktive Turniere, Nächstes Turnier und
  Turnierarchiv; Zeile 2 zeigt Schützen, Regelwerke und Bogenklassen.
- **Aktivitätspanel unter Kacheln**: Das „Letzte Aktivität"-Panel ist zurück unter den
  Dashboard-Kacheln und per vertikalem QSplitter in der Höhe veränderbar.
- **Einstellungen/Druck-Labels**: „Vereinslogo einfügen" (vorher „Vereinslogo einfügen in")
  und „Einzelwertung einfügen" (vorher „Einzelwertung je Scheibe in Liste").
- **Vereinslogo-Einstellung zusammengeführt**: Die separate Option „Vereinslogo klein am Ende
  der Ausschreibung wiederholen" wurde entfernt. Die Option „Vereinslogo einfügen" steuert jetzt
  beide Ausgaben (Ergebnisliste und Ausschreibungs-Footer).
- **Turnierliste filtert abgeschlossene Turniere**: Neue Checkbox „Abgeschlossen anzeigen"
  (Standard: ausgeblendet) in der Turnierliste.
- **Seitenleiste eingeklappt**: Einstellungen, „Über BowTally" und Theme-Umschalter bleiben im
  eingeklappten Zustand sichtbar (Icon-only). Nav-Liste kann auf minimale Icon-Breite schrumpfen.
- **Phasenwechsel-Protokoll-Button**: Jetzt so breit wie der Nächste-Phase-Button.
- **QCheckBox sichtbar**: Checkboxen im Einstellungsdialog erhalten explizites Styling
  (Rahmen, Hintergrund, Primary-Farbe für den aktivierten Zustand).

### Behoben

- **Sidebar-Burger**: Icon fehlte → Burger-Button nutzt jetzt `QToolButton` mit Theme-Icon.
- **Sidebar-Einklappen**: Logo und App-Titel wurden nicht ausgeblendet; beim Aufklappen wurde
  fälschlicherweise in ein Turnier navigiert (nav-Signale nicht geblockt).
- **Textboxen Beschreibung/Notizen**: Mehrzeilige Eingabefelder im Vereinsprofil zeigten nur
  eine Zeile; fixe Höhe (90 px) wie die Textvorlagen-Boxen im Druck-Tab.

## [0.6.0] – 2026-10-20

### Hinzugefügt

- **Phasenwechsel rückwärts**: Neue Schaltfläche „← Vorherige Phase" (rot) im Sidebar-Navigator
  und „← Zur vorherigen Phase" im Protokoll-Dialog ermöglichen das manuelle Zurücksetzen der Phase.
  Jeder Rückwärts-Wechsel wird als erzwungen im Protokoll festgehalten.
- **Erststart-Assistent**: Beim ersten App-Start ohne Vereinsname erscheint ein überspringbarer
  Einrichtungsdialog für Vereinsname, Ort und Verband.
- **Backup-Tab in Einstellungen**: Lokales ZIP-Backup (NAS/USB) mit konfigurierbarer
  Aufbewahrungsanzahl, Nextcloud-Upload per WebDAV sowie Wiederherstellung aus einer ZIP-Datei.
- **Dashboard-Kacheln Regelwerke und Bogenklassen**: Zwei neue klickbare Kacheln auf dem
  Haupt-Dashboard; ein Klick navigiert direkt zur jeweiligen Ansicht.
- **Aktivitäts-Panel rechts**: Das „Letzte Aktivität"-Panel wurde auf die rechte Seite des
  Haupt-Dashboards verschoben und ist über eine ◀/▶-Schaltfläche ein-/ausblendbar.
- **Turnier-Dashboard-Kacheln klickbar**: Teilnehmer-, Einnahmen-, Fortschritts- und Phasen-Kachel
  im Turnier-Dashboard navigieren per Klick zur zugehörigen Ansicht.
- **Vereinsvorstand-Kontakte**: Fünf Vorstandsrollen (1./2. Vorsitzende/r, Kassenwart/in,
  Sportleiter/in, Bogenreferent/in) mit Vor- und Nachname im Vereinsprofil hinterlegbar.
  Datenbank-Migration 0005 fügt die zehn neuen Spalten hinzu.
- **Turnier-Assistent Kontaktseite**: Dropdown zur Auswahl einer Vorstandsperson als
  Kontaktname des Turniers.

### Geändert

- **Sidebar resizierbar**: Die linke Seitenleiste ist per Maus (QSplitter) in der Breite
  veränderbar und über einen Burger-Button in einen Icon-Only-Modus kollabierbar.
- **App-Logo klickbar**: Ein Klick auf das Logo oben links navigiert immer zum Haupt-Dashboard.
- **Check-in-Verbesserungen**: Die Schaltfläche „Als Walk-in erfassen" wurde neben
  „Einchecken" verschoben (rot), die Enter-Taste löst das Einchecken nicht mehr automatisch aus.
- **Gebühren-Tab ausgeblendet**: In den Phasen Schießen, Wertung und Abgeschlossen wird der
  Gebühren-Tab im Turnier-Detail ausgeblendet.
- **Einstellungen-Beschriftungen**: Einheitliche Label-Breite (130 px) und mehrzeilige
  Textfelder mit Mindesthöhe für 4 Zeilen statt fixer Höhe.
- **Turnier-Assistent Zusammenfassung**: Tabellen-Zellbreite per HTML-Attribut gesetzt,
  sodass Schlüssel und Werte in einer Spalte ausgerichtet sind.

### Behoben

- **Einnahmen-Dashboard zeigt 0 €**: Wenn `fee_amount_paid` nicht gesetzt war, wurde fälschlich
  0 € angezeigt. Jetzt wird auf den Gebührenbetrag der zugewiesenen Startgebühr zurückgegriffen.

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

[Unveröffentlicht]: https://github.com/jenskaesler/bowtally/compare/v2026.10.4...HEAD
[2026.10.4]: https://github.com/jenskaesler/bowtally/compare/v2026.10.1...v2026.10.4
[2026.10.1]: https://github.com/jenskaesler/bowtally/compare/v2026.10.0...v2026.10.1
[2026.10.0]: https://github.com/jenskaesler/bowtally/compare/v0.7.0...v2026.10.0
[0.7.0]: https://github.com/jenskaesler/bowtally/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/jenskaesler/bowtally/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/jenskaesler/bowtally/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/jenskaesler/bowtally/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/jenskaesler/bowtally/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/jenskaesler/bowtally/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/jenskaesler/bowtally/releases/tag/v0.1.0
