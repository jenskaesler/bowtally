# Changelog

Alle nennenswerten Änderungen an BowTally. Format nach
[Keep a Changelog](https://keepachangelog.com/de/1.1.0/), Versionierung nach
dem Schema `yyyy.MM.patch` (Jahr.Monat.Patch).

## [Unveröffentlicht]

## [2026.11.4] – 2026-11-17

### Hinzugefügt

- **👥 Mitglieder-Stammdaten** — Die Helfer-Stammdaten sind zu Mitglieder-Stammdaten
  ausgebaut (Hauptmenü „Mitglieder"): Mitgliedsnummer, Adresse, Mitglied seit/gekündigt zum,
  Geburtstag, Einwilligung zur Datenverarbeitung (Warnung statt Sperre), Bankverbindung mit
  IBAN-Prüfziffer und SEPA-Mandat sowie eine Helferhistorie (Tab nur bei „Ist Helfer“), Notizen und
  Dateien in einem eigenen Tab. Bestehende Helfer und Turnier-
  Zuordnungen werden einmalig migriert (vorher entsteht automatisch eine Kopie
  `bowtally.db.pre-migration-<Revision>`). Bankdaten erscheinen in keinem Export.
- **📨 Datenauskunft** — Statt „E-Mail senden" öffnet die Mitgliederliste jetzt einen Mailentwurf
  „Datenauskunft senden" mit allen gespeicherten Daten des Mitglieds (Art. 15 DSGVO). Die IBAN
  ist bis auf die letzten vier Stellen durch Sternchen ersetzt. Der Text ist unter
  Einstellungen → E-Mail-Vorlagen → Datenauskunft anpassbar (Platzhalter `{daten}`).
- **🎯 Kills und X-Treffer je Regelwerk** — Im Regelwerk lassen sich „Kills zählen“ und „X-Treffer
  zählen“ ein- und ausschalten, jeweils mit „Bei gleicher Punktzahl gewinnt die höhere Anzahl“.
  Kills zählen nur bei der neuen Regelwerk-Disziplin „3D-Parcours“, X-Treffer nur bei „Scheibe“
  (bei bestehenden Regelwerken aus dem Namen abgeleitet).
  Bei „Gesamtwertung“ und „Pro Runde“ gibt es dafür eine Spalte neben den Punkten; sie erscheint
  auch in Ergebnisansicht und PDF. Die JSON-Eingabe „Sonderregeln“ ist durch Schalter ersetzt,
  die Tie-Break-Einstellung (englische Begriffe) wandert ins Regelwerk: Kills, X-Treffer, dann
  Treffer in der höchsten Wertung; bleibt es gleich, teilen sich Teilnehmer den Rang. Neu: „Diese
  Treffer vor Kills und X-Treffern prüfen“ (Reihenfolge je Regelwerk, z. B. DBSV-Außenrunde) und
  „Stechen erforderlich“ (Hinweis bei Gleichstand auf Platz 1–3 in Ergebnisansicht, PDF und beim
  Abschließen, passend zu IBO und IFAA).
- **📤 Regelwerke lesbar exportieren und importieren** — Statt JSON-Spalten enthält die Tabelle
  Disziplin, Schüsse je Ziel, Nachschuss, die Zonen als Text (`Kill-Zone = 11 [Kill]; Körper = 8`)
  und Ja/Nein-Spalten für Kills, X-Treffer und Treffer in der höchsten Wertung. Ältere Dateien mit
  JSON-Zonen lassen sich weiter importieren.
- **🥇 Stechen eintragen** — Bei Regelwerken mit „Stechen erforderlich“ erscheint in der Auswertung
  der Button „Stechen eintragen“: Punkte des Stechens je Teilnehmer, der höhere Wert gewinnt den
  Gleichstand. Sobald Werte eingetragen sind, zeigen Ergebnisansicht, Excel-Exporte und PDF eine
  Spalte „Stechen“. Gespeichert im Backup, bis zur Ergebnisliste änderbar; die Rückfrage beim Erstellen
  der Ergebnisliste warnt vor offenen Gleichständen.
- **🤝 Turnier-Helfer** — Neben „Neuer Helfer" (nur für das Turnier) gibt es „Aus
  Mitgliederkartei" (nur aktive Mitglieder mit Flag „Turnierhelfer"). Beim Abschluss eines
  Turniers wird die Helferhistorie der verknüpften Mitglieder automatisch ergänzt.
- **🔐 Backup mit Passwort** — Backups sind AES-256-verschlüsselte ZIP-Dateien. Das Passwort
  ist ein Pflichtfeld (manuell oder per „Passwort vorschlagen") und wird bei jeder
  Wiederherstellung abgefragt. Alte unverschlüsselte Backups und Backups mit Helfer-Struktur
  lassen sich weiterhin wiederherstellen (Format 2, alte Backups werden automatisch migriert).
- **📜 Urkunden – neues Layout** — Genau eine A4-Seite je Podiumsplatz und Klasse mit
  Doppelrahmen, Vereinslogo und -name, Siegel in Gold/Silber/Bronze, Name, Klasse, Punkten,
  Turniername sowie Unterschriftszeilen (Ort/Datum, 1. Vorstand). Zu lange Namen werden
  automatisch verkleinert.
- **💾 Backup als ZIP** — Enthält `backup.json` mit allen Tabellen (zusätzlich Aktivitätslog,
  Backup-Log, Turnier-Bogenklassen), das Vereinslogo und die Prüfdatei `bowtally.info`
  (Typ, App- und Schema-Version, Zeitstempel). Die Wiederherstellung validiert die Prüfdatei
  und legt das Logo wieder im Programmverzeichnis ab. Alte JSON-Backups werden nicht mehr
  importiert.
- **⚙️ Einstellungen – Speichern-Button** — „Speichern" ist grau und wird rot, sobald sich
  etwas geändert hat; beim Schließen mit ungespeicherten Änderungen erscheint eine Rückfrage.
- **📝 Notizen im Turnierdialog** — „Notizen (intern)" auf Seite 1 wird als Turniernotiz
  gespeichert. Im Dashboard und im Leitfaden (Phase „Abgeschlossen") erscheinen die Notizen
  jeweils in einer eigenen Box.
- **ℹ️ Über BowTally** — Changelog wird aus `CHANGELOG.md` geladen (Installation:
  `docs\CHANGELOG.md`), statische Links zu Changelog und Releases auf GitHub.
- **❓ Hilfe** — Von 8 auf 20 Abschnitte erweitert (u. a. Notizen, Backup, Updates,
  E-Mail-Versand, Helfer, Inventar, Logbuch).
- **✉️ E-Mail-Schriftart** — Alle E-Mail-Entwürfe mit Anhang verwenden die Schriftart aus
  Einstellungen → Oberfläche in Schriftgröße 10 pt; ist sie nicht installiert, gilt die Schriftart
  des Mailprogramms (die Größe bleibt 10 pt).

### Geändert

- **🧭 Menü „Regeln“** — Der Eintrag „Regelwerke“ in der Seitenleiste heißt jetzt „Regeln“.
- **🪟 Dialoge** — Formulare öffnen standardmäßig so groß, dass der gesamte Inhalt zu sehen ist
  (gespeicherte Dialoggrößen werden dafür einmalig zurückgesetzt). Im Mitglieder-Dialog steht der
  Button „Aus Basisdaten übernehmen“ in der Zeile „Kontoinhaber“.

- **📏 Standard-Regelwerke nach den Verbandsregeln** — Gleichstandsregeln der eingebauten Regelwerke
  entsprechen jetzt WA, IBO, IFAA und DBSV (z. B. WA Halle: 10er, dann 9er, ohne X; IBO: 11er und
  Stechen; IFAA Feld: Stechen). Bei jedem Start werden die eingebauten Regelwerke daran angeglichen.
- **🗑️ Regelwerke ohne belegbare Quelle entfernt** — ASA 3D, NFAA 3D, 3D Standard 3-Pfeil, DBSV
  3D-Jagdrunde und Blasrohr Standard (Migration 0033). Nutzt ein Turnier eines davon, bleibt es als
  eigenes Regelwerk erhalten. Das Standard-Regelwerk für neue Turniere ist jetzt „3D Hunter (IBO)“.

- **🎯 „Pro Ziel“** — Der Wertungsmodus „Scheibenwertung“ heißt jetzt „Pro Ziel“; Meldungen und
  Hilfetexte sprechen von Zielergebnissen.
- **💾 Backup (Format 4)** — Die Regelwerk-Optionen (Disziplin, Zähler, Gleichstand) und die Dateien der
  Mitglieder (Ordner `member_files` im Datenordner) sind im Backup enthalten.
  Die überflüssige globale Einstellung „Tie-Break-Logik“ wurde entfernt (Migration) und
  wird beim Wiederherstellen alter Backups ignoriert. Backups der Formate 1 bis 3 lassen sich weiter
  wiederherstellen.
- **🏹 Eingebaute Regelwerke** — Zonen mit eindeutiger Bedeutung (Killzone, Miss, X) haben jetzt
  einen Typ, damit „Pro Ziel“ Kills, Fehlschüsse und X automatisch zählt.

- **🎯 Auslosung nur bei Bedarf** — „Auslosung durchführen" im Leitfaden, in der Rückfrage
  beim Phasenwechsel und „Auslosung …" im ⋮-Menü der Teilnehmer erscheinen nur, wenn die
  Auslosung im Turnierdialog gewählt wurde.
- **🙋 Helfer** — Der Tab „Helfer“ im Turnier zeigt nur noch die Helfer dieses Turniers; die
  Stammdaten stehen unter „Mitglieder“ in der Seitenleiste.
- **📑 Turnierdetails** — Die Tabs „Preise" und „Helfer" stehen direkt hinter „Teilnehmer".
- **🧙 Turnierdialog** — Seite 4: „Einschreibung ab", „Schießbeginn" und Einschießen stehen
  über der maximalen Teilnehmerzahl. Die Checkbox „Ausschreibung jetzt generieren" samt
  Footer-Rest auf Seite 8 entfällt.
- **🏁 Einschreibung** — Der Walk-in-Button bleibt auch bei erreichter Teilnehmerzahl nutzbar.
- **🏆 Preise** — Der Button „Preis- und Siegerliste" ist nur noch in der Auswertung zu finden.
- **🍔 Burger-Buttons** — Einheitlich quadratisch mit zentriertem Icon; Kontextmenüs setzen
  einen Trennstrich vor „Entfernen"/„Löschen".
- **🧭 Seitenleiste** — Trennlinie über „Einstellungen".
- **🚀 Erststart-Dialog** — Öffnet mittig über dem Hauptfenster, 15 % größer; „Abbrechen"
  beendet die Anwendung.
- **🔄 Update-Prüfung** — Netzwerk- und Serverfehler werden verständlich angezeigt.

### Behoben

- **🎯 Ergebniseingabe** — Bei „Rundenwertung“ und „Nur Gesamtpunkte“ fehlten Suche, Speichern-Button,
  Gruppen-Dropdown und Klassen-Tabs; die Leiste steht jetzt bei allen Wertungsarten über der Tabelle
  und filtert auch dort. Die Klassen-Tabs hängen wie in der Auswertung direkt über der Liste und
  zeigen die vollen Klassennamen; die Tabelle nutzt dieselben Abstände und Ausrichtungen.
- **👥 Mitglieder-Notizen** — Im Tab „Notizen“ steht das Label über dem Textfeld, das die volle Breite
  nutzt.

- **📦 Excel „Turnier komplett“** — Das Blatt „Ergebnisse“ enthält jetzt auch bei „Rundenwertung“ und
  „Nur Gesamtpunkte“ die Werte, bei mehreren Runden alle Runden, dazu die Kill-/X-Spalten; die
  „Rangliste“ nennt Kills/X.
- **💾 Wiederherstellung** — Eingebaute Regelwerke werden über ihren Namen zugeordnet (ihre Nummern
  unterscheiden sich zwischen Versionen), Turniere und das Standard-Regelwerk behalten ihr Regelwerk.
  Entfernte Regelwerke kommen nur zurück, wenn ein Turnier sie nutzt; eigene Regelwerke
  überschreiben keine eingebauten mehr.

- **⚙️ Backup-Einstellungen** — Die Box „Backup-Speicherort“ staucht bei Nextcloud nicht mehr die
  Zeilen und schneidet keine Buttons mehr ab; der Tab scrollt bei kleinem Fenster.

- **⚙️ Einstellungen schließen** — „Schließen" ohne Änderungen tat nichts, und „Abbrechen" der
  Rückfrage schloss den Dialog trotzdem.
- **🎯 `use_draw` wurde nicht gespeichert** — Die Auslosungs-Option aus dem Turnierdialog
  ging beim Speichern verloren.
- **📑 Phasenwechsel** — Nach dem Ausblenden des aktiven Tabs bleibt dessen Nachfolger nicht
  mehr leer.
- **🎯 Ergebniseingabe** — Der Hinweis „unvollständige Zielergebnisse" beim Wechsel nach
  „Auswertung" und der Fortschritt in Leitfaden und Dashboard berücksichtigen jetzt die
  Wertungsart (Gesamtwertung: ein Wert, pro Runde: ein Wert je Runde) und mehrere Runden.
  Gesamt- und Rundenwerte akzeptieren nur Ziffern, ein abgelehnter Wert zeigt wieder den
  gespeicherten Wert, „Nur unvollständige" wirkt auch in diesen Tabellen, und das Spalten-Menü
  respektiert die Sperre nach der Ergebnisliste.

## [2026.11.3] – 2026-11-16

### Hinzugefügt

- **📜 Lizenztext** — Aus `docs/license.txt` im Erststart-Assistenten und im About-Dialog.
- **✉️ Ausschreibung per E-Mail** — Der Entwurf öffnet sich nach der PDF-Erzeugung (nicht mehr
  beim Anlegen des Turniers) mit dem PDF im Anhang (`.eml`).
- **✉️ Ergebnisversand** — Ergebnisliste als PDF-Anhang; Vorlage ohne Verweis auf die Website.
- **🏹 Schützen – „Ergebnisversand per E-Mail"** — Neues Feld `notify_results` (Migration 0025,
  nur mit E-Mail-Adresse aktivierbar); die Schützen sind im Empfängerdialog vorausgewählt.
- **🏆 Auswertung sperren** — Buttons erst nach dem Erstellen der Ergebnisliste aktiv, danach
  mit Rückfrage und nur lesbar; PDF im Export-Menü, „Als PDF speichern" entfällt.
- **📝 Tab „Notizen"** — Freitext je Turnier (Migration 0027, nach Abschluss nur lesbar), im
  Turnier-Export zusammen mit der Nachbesprechung.
- **📏 Turnierregeln und Teilnahmebedingungen** — Globale Texte im Tab „Turnierregeln"
  (Migration 0028), als PDF exportierbar und als Zusatzseite in der Ausschreibung.
- **🙋 Helfer in den Turnierdetails**, Hamburger-Menüs und Icons in allen Kontextmenüs.

### Geändert

- **🎯 „3D Standard 3-Pfeil"** ist das Standard-Regelwerk; „+ Runde" übernimmt die
  Standard-Pfeile.
- **🧙 Turnierdialog** — „Einschießen erlaubt" standardmäßig aus, Einschießbereich Pflicht,
  Schaltflächen „Vereinsdaten übernehmen" funktionieren wieder; Startgruppen sind bei
  Auslosung schreibgeschützt.
- **📑 Turnierdetails** — „Turnierdaten bearbeiten" ab Vorbereitung ausgeblendet; Parcours,
  Zeitplan und Preise in „Abgeschlossen" nur lesbar; Ergebniseingabe mit Filter links.
- **🔄 Update-Prüfung** — Button und Datum rechtsbündig; das Datum aktualisiert sich nach
  manueller Prüfung.

### Behoben

- **💾 Backup-Wiederherstellung** — FK-Fehler: Die temporäre Datenbank wird vor dem Import
  mit den Standarddaten befüllt.
- **📄 Ausschreibung** — Doppelter Block „Wichtige Hinweise" entfernt.

## [2026.11.2] – 2026-11-13

### Hinzugefügt

- **🔄 Automatische Updates** — Prüfung der GitHub-Releases, Update-Dialog mit Changelog-Auszug,
  Download mit SHA-256-Prüfsumme und stille Installation; in den Einstellungen abschaltbar,
  mit manuellem „Jetzt prüfen" und Datum der letzten Prüfung.
- **✉️ E-Mail-Vorlagen** — Überarbeitet mit weiteren Platzhaltern (u. a. Startgruppe, Startnummer,
  Zeiten, Kontoinhaber, Kontakt), Signatur mit Vereinslogo und neuer Vorlage für die
  Turnierausschreibung; Warteliste standardmäßig automatisch.
- **🚀 Erststart-Assistent** — Zweite Seite mit Lizenz, die akzeptiert werden muss.
- **📁 Dokumentation** — Benutzeranleitungen unter `docs/`, überarbeiteter Installer.

### Geändert

- **⚙️ Einstellungen** — Neue Seite „Allgemein" unter „System" (Update-Prüfung, Speicherorte),
  „Druck" heißt „Druck & Listen"; neue Standard-Reihenfolge der Seitenleiste.
- **📑 Phasenwechsel** — Bei ausgeblendetem Tab wird auf den ersten sichtbaren gewechselt.

### Behoben

- **🗄️ Migrationen** — Phase „Entwurf" (0006) und Vorlagen-Schlüssel (0023) werden idempotent
  angelegt; Standarddaten werden bei jedem Start ergänzt, sodass der Einstellungsdialog alle
  Felder zeigt.

## [2026.11.1] – 2026-11-02

### Hinzugefügt

- **📊 Dashboard – Draggable Tiles** — Die neun Module (Aktive Turniere, Nächstes Turnier,
  Archiv, Schützen, Regelwerke, Bogenklassen, Helfer, Inventar, Kalender) erscheinen als
  ziehbare Kacheln in einem 3×3-Raster. Die Reihenfolge wird per Drag & Drop verändert
  und dauerhaft gespeichert.
- **📊 Dashboard – Helfer, Inventar, Kalender** — Drei neue Kacheln zeigen Gesamtanzahl und
  Direktlink in die jeweilige Ansicht.
- **🗄️ Datenbank – Migration 0020** — Neue JSON-Spalten `tracked_specials` (in
  `scoring_rules`) und `specials` (in `scores`) als Grundlage für Kill- und X-Ring-Zählung.
  Alle 14 eingebauten Regelwerke erhalten beim Migrations-Lauf automatisch die passenden
  `tracked_specials`-Definitionen (Kill, X, 12-Ring, Miss je nach Format).

### Geändert

- **🎨 Seitenleiste** — Hintergrundfarbe entspricht jetzt dem App-Hintergrund. Nur die
  Trennlinie grenzt Sidebar und Inhalt ab.
- **📅 Kalenderansicht – Styling** — Tageszellen, Mini-Monate und die Ansichts-Umschaltknöpfe
  (Jahr/Monat/Woche) erhalten QSS-basierte Rahmenstile und Hover-Effekte statt nativer Qt-Rahmen.
- **📅 Kalenderansicht – Layout** — Monats-, Wochen- und Jahresraster füllen jetzt die
  verfügbare Fensterhöhe gleichmäßig aus (Row-Stretch statt trailing Spacer).
- **📅 Kalenderansicht – Heute-Highlight** — Der heutige Tag wird in Mini-Monaten mit
  Primary-Farbe hervorgehoben. Turnier-Badges zeigen Pointer-Cursor und emittieren
  Hover-Signale für die Turniervorschau.
- **⚙️ Einstellungen – Navigation** — Eintrag „Turniere" ergänzt. Auswahl-Highlight in
  Einstellungen und Hilfe nutzt jetzt volle Primary-Füllung statt Border-only.
- **📋 Leitfaden** — Dauerhaft aus der Seitenleiste ausgeblendet. Nur noch über den
  Turnier-Navigator erreichbar.

## [2026.10.9] – 2026-10-31

### Hinzugefügt

- **ℹ️ „Über BowTally"** — Im neuen Sidebar-Layout: linke Navigation mit vier Punkten
  (Über BowTally, Lizenz, Changelog, Tastenkürzel), gleiches Design wie Hilfe- und
  Einstellungs-Dialog.

### Geändert

- **💾 Backup-Format** — Backups werden jetzt als JSON-Datei gespeichert
  (`BowTally-Backup-YYYY-MM-DD-HHMMSS.json`) statt als ZIP. Das JSON enthält Metadaten
  (Version, Alembic-Schema) und alle Tabelleninhalte als Row-Dicts mit ISO-Datetime-Werten.
  Wiederherstellen aus JSON baut eine frische Datenbank via Alembic-Migrationen und
  importiert die Daten spaltenfiltriert. Alte ZIP-Backups können nicht mehr importiert werden
  (Hinweis-Dialog). Aufbewahrung berücksichtigt sowohl neue JSON- als auch alte ZIP-Dateien.
- **🎨 Design-Einstellungen** — Modus-Auswahl (Hell/System/Dunkel) in eigene GroupBox
  „Darstellung" eingebettet.
- **🔲 Wechselzeilen (Zebra-Striping)** — In allen Tabellen der App: Gebührentabelle und
  Rundentabelle im Turnier-Assistenten, Import-Vorschau, Helfer-Verlaufstabelle.
- **⚙️ Einstellungen – Navigation** — Listeneinträge erhalten abwechselnde Zeilenhintergründe
  und 36 px Mindesthöhe.
- **🧙 Turnier-Assistent** — Wizard-Stil auf `ModernStyle` umgestellt. Keine doppelte
  Trennlinie mehr über den Navigations-Buttons.
- **🧙 Turnier-Assistent Seite 4** — `setVerticalSpacing(8)` gilt jetzt einheitlich für alle
  Formular-Seiten. Zeitfelder „Einschreibung ab" und „Schießbeginn" zeigen `--:--`
  als Leer-Zustand.

## [2026.10.7] – 2026-10-31

### Hinzugefügt

- **📐 Parcours-Tab** — Im Turnier-Detail (ab Phase Vorbereitung): Nummer, Tier/Scheibe,
  Distanz, Pfeilstopp-Klasse, Geländetyp, maximale Gruppengröße und Helferhinweis je Ziel.
  Reihenfolge per Drag-and-Drop. Druckfunktionen **Aufbauplan** und **Scheibenplan** als PDF.
- **🗓️ Zeitplan-Tab** — Startgruppen mit Startzeit und geschätzter Dauer. Druckfunktion
  **Zeitplan-Aushang** als PDF.
- **📅 Jahreskalender** — Monatsraster mit allen Turnieren als farbige Badges nach Phase.
  Jahreswahl per Spinner. Klick auf ein Turnier öffnet es direkt. ICS-Export.
- **📋 Wertungszettel-Vorlagen** — Globale Verwaltung mit konfigurierbaren Spalten (Name, Typ,
  Breite) per Drag-and-Drop-Editor. Vier eingebaute Vorlagen: 3D-Standard, Feld-Standard,
  Halle 10-Ring, Blasrohr-Standard.
- **🎯 Auslosung** — Automatische Gruppeneinteilung: Gruppengröße, Rotation (sequenziell/zufällig),
  optional getrennt nach Bogenklasse. Weist Startgruppe, Startnummer und Startscheibe zu.
  Optional direkt im Anschluss Wertungszettel drucken.
- **🏆 Preise-Tab** — Preise je Turnier mit Rang, Name, Bogenklasse (optional), Beschreibung
  und Wert. Beim Klonen werden Preise mit übernommen.
- **📜 Urkunden-PDF** — Eine Seite je Podiumsplatz mit konfigurierbaren Textblöcken und
  Platzhaltern (`{name}`, `{klasse}`, `{platz}`, `{punkte}`, `{turniername}`, `{datum}`).
- **🥇 Preis- und Siegerliste** — Rangliste je Bogenklasse mit zugewiesenen Preisen als PDF.
- **📋 Starterfeld-Liste** — Alle aktiven Teilnehmer als PDF, sortierbar nach Startnummer oder
  Startgruppe.
- **📋 Gruppen-Aushang** — Eine Seite je Startgruppe mit Teilnehmerliste, Startscheibe und
  Scheibenübersicht als PDF.
- **📋 Leitfaden – Auslosung** — Neue Aufgabe „Auslosung durchführen" mit Direktlink in der
  Einschreibungsphase.

### Geändert

- **📋 Turnier kopieren** — Parcours-Ziele und Preise werden beim Klonen mit übernommen.
- **🏆 Auswertungs-Tab** — Neue Schaltflächen „Urkunden drucken" und „Preis- und Siegerliste"
  in der Button-Leiste (ab Phase Schießen).
- **👥 Teilnehmerverwaltung** — Menü „Weitere ▾" enthält jetzt „Auslosung …" und
  „Starterfeld drucken".

## [2026.10.6] – 2026-10-25

### Hinzugefügt

- **🗔 Modal-Dialoge für Stammdaten** — Bogenklassen, Regelwerke, Helfer und Schützen öffnen
  beim Anlegen und Bearbeiten eigenständige Dialoge statt einer Seitenleiste. Jeder Dialog
  enthält alle Felder, Pflichtfeldmarkierung, Inline-Validierung und Dirty-Check beim
  Schließen.
- **👷 Helfer-Bearbeitungsdialog** — Im globalen Modus wird die bisherige Turnierbeteiligung
  des Helfers als schreibgeschützte Tabelle angezeigt.
- **📐 Größe der Dialoge speichern** — Die Fenstergröße jedes Dialogs wird beim Schließen
  gespeichert und beim nächsten Öffnen wiederhergestellt.

### Verbessert

- **📐 Dialoge skalierbar** — Die Stammdaten-Dialoge sind frei per Maus skalierbar (zuvor
  feste Breite 560 px).
- **🔘 Schaltflächenreihenfolge** — In allen neuen Dialogen folgt „Abbrechen" rechts neben
  „Speichern" (Windows-Konvention).

### Behoben

- **❌ X-Button der Dialoge** — Das Setzen von `setWindowFlags()` nach der Konstruktion hat
  auf Windows den nativen Schließen-Button deaktiviert. Der Aufruf wurde entfernt.

## [2026.10.4] – 2026-10-25

### Hinzugefügt

- **🔁 Multi-Runden-Turniere** — Turniere können aus mehreren Runden bestehen. Drei
  Wertungsmodi: je Scheibe (`per_target`), je Runde (`per_round`) oder Gesamtwertung
  (`total_only`). Jede Runde hat eine eigene Bezeichnung, ein eigenes Regelwerk, Scheibenzahl,
  Pfeile und Entfernungstyp.
- **🧙 Turnier-Assistent – Konfigurationsseite neu** — Rundenstruktur direkt in einer Tabelle
  pflegen (Bezeichnung, Regelwerk, Scheiben, Pfeile, Entfernung). Zeilen per „+ Runde" ergänzen
  oder per Löschen-Button entfernen.
- **📏 14 integrierte Regelwerke** — Zu den drei eingebauten Regelwerken (IBO 3D, ASA 3D,
  WA 3D) kommen elf weitere: 3D Hunter (IBO), 3D Standard 3-Pfeil, Feldbogen IFAA
  (bekannte/unbekannte Entfernung), WA Halle 18 m (mit X-Ring-Tiebreak), Blasrohr Standard,
  DBSV 3D-Waldrunde, DBSV 3D-Jagdrunde, IBO 3D mit 12-Ring, NFAA 3D, WA Halle 25 m.
- **📋 Leitfaden** — Aufgabe „Rundenstruktur konfiguriert" in der Vorbereitungsphase.

### Behoben

- **☁️ Nextcloud-Backup** — HTTP 409 (Conflict) beim Erstellen bereits existierender Ordner
  wird jetzt korrekt ignoriert. Nextcloud weicht hier vom WebDAV-Standard ab (405 statt 409).

## [2026.10.1] – 2026-10-24

### Verbessert

- **✅ UX: Checkbox-Labels** — „Abgeschlossene Turniere anzeigen" und „Inaktive Schützen
  anzeigen" (präzisere Formulierungen).
- **💶 Leitfaden – Einnahmen** — Navigiert jetzt direkt zum Turnier-Dashboard statt zur
  globalen Übersicht.
- **🖱️ Rechtsklick-Menüs** — Tooltips entfernt. Bedingungen im Teilnehmer-Menü präzisiert
  (Bestätigen nur für Gemeldet/Warteliste, Zahlung nur bei hinterlegter Gebühr,
  DNS/Zurückziehen nur für aktive Teilnehmer).
- **❓ App-Hilfe** — Umbau von Tab-Widget auf geteilte Ansicht (Liste links, Inhalt rechts).
  9 Abschnitte auf 7 zusammengeführt. Neuer Abschnitt „Rechtsklick-Menüs".

## [2026.10.0] – 2026-10-24

### Hinzugefügt

- **👥 Vereinsvorstand-Tab** — Eigener Tab in den Einstellungen für alle fünf Vorstandsrollen
  (1./2. Vorsitzende/r, Kassenwart/in, Sportleiter/in, Bogenreferent/in) mit Vorname,
  Nachname, Telefon und E-Mail. Migration 0007 fügt die zehn neuen Spalten hinzu.
- **👥 Übernehmen-Button im Turnier-Assistenten** — Auf der Kontaktseite übernimmt ein Klick
  Name, Telefon und E-Mail der gewählten Vorstandsrolle direkt in das Formular.
- **👥 Standard-Kontaktperson** — Im Vereinsprofil-Tab wählbar, welche Vorstandsrolle bei
  neuen Turnieren als Kontakt vorbelegt wird.
- **❓ App-Hilfe (F1)** — Dialog mit Inhaltsverzeichnis und neun Abschnitten: Übersicht,
  Turniere, Schützen, Ergebnisse, Regelwerke, Einstellungen, Platzhalter-Referenz,
  Tastenkürzel, Backup.
- **🌟 Splash-Screen** — Beim Start: Vereinslogo, App-Name, Version, Fortschrittsbalken;
  passt sich dem hellen und dunklen Systemthema an.
- **❓ Hilfe-Eintrag** — In der Seitenleisten-Navigation (neben Einstellungen und Über BowTally).

### Geändert

- **📋 Turnier kopieren** — (vorher „Klonen") Aktion und Tooltip umbenannt.
- **⚙️ Einstellungsbeschriftungen** — Kurze, einheitliche Labels für Sprache, Schriftart,
  Papiergröße, Format, Tie-Break-Logik und Verwendungszweck. Alle Formular-Labels auf
  einheitliche Breite (130 px) ausgerichtet.
- **🔄 Wizard Nächste-Phase-Button** — Pfeilzeichen (›) aus dem Label entfernt.
- **❓ Hilfe-Symbol in der Statusleiste** — Öffnet jetzt die App-Hilfe statt das
  Tastenkürzel-Formular.
- **🎨 Theme-Umschalter** — Aus der Seitenleiste entfernt. Darstellung weiterhin in
  Einstellungen → Design änderbar.
- **❓ Oberes Hilfe-Menü** — Entfernt. Hilfe ist über F1, Statusleiste und Seitenleiste
  erreichbar.

### Entfernt

- **📝 Notizen-Feld** — Aus dem Vereinsprofil entfernt.
- **⌨️ Tastenkürzel-Formular** — Eigenständiger Dialog entfernt. Tastenkürzel sind jetzt
  in der App-Hilfe unter „Tastenkürzel" zu finden.

## [0.7.0] – 2026-10-20

### Hinzugefügt

- **🔄 Phase „Entwurf"** — Neue erste Phase vor der Ausschreibung. Neue Turniere starten im
  Entwurfsstatus; alle Daten frei bearbeitbar. Ab der Einschreibungsphase ist der
  Turnier-Assistent gesperrt. Migration 0006 fügt die Phase in bestehende Datenbanken ein.
- **📋 Turnier klonen** — Aus dem Aktionsmenü der Turnierliste: bestehendes Turnier als
  Vorlage klonen. Assistent startet vorausgefüllt; Teilnehmer und Ergebnisse werden nicht
  übernommen.
- **📊 Dashboard-Kachel „Turnierarchiv"** — Zeigt Anzahl abgeschlossener Turniere und führt
  per Klick zur Turnierliste.
- **💾 Automatisches Backup beim Beenden** — Neuer Schalter im Backup-Tab. Beim Schließen
  der App wird ein lokales ZIP-Backup erstellt, sofern ein Backup-Pfad gesetzt ist.
- **ℹ️ About-Dialog** — Neuer Eintrag „Über BowTally" in der Seitenleiste mit Versionsnummer,
  Kurzbeschreibung, GitHub-Link, Entwicklerinfo und Lizenzhinweis.
- **📜 Lizenz** — Eigene Nicht-Kommerzielle-Copyleft-Lizenz eingeführt.

### Geändert

- **📊 Dashboard-Kacheln neu geordnet** — Zeile 1: Aktive Turniere, Nächstes Turnier,
  Turnierarchiv. Zeile 2: Schützen, Regelwerke, Bogenklassen.
- **📊 Aktivitätspanel** — „Letzte Aktivität"-Panel ist zurück unter den Dashboard-Kacheln;
  per vertikalem QSplitter in der Höhe veränderbar.
- **🖨️ Einstellungen/Druck-Labels** — „Vereinslogo einfügen" (Option steuert jetzt
  Ergebnisliste und Ausschreibungs-Footer gemeinsam).
- **📋 Turnierliste** — Filtert abgeschlossene Turniere. Neue Checkbox „Abgeschlossen anzeigen"
  (Standard: ausgeblendet).
- **🗂️ Seitenleiste eingeklappt** — Einstellungen, „Über BowTally" und Theme-Umschalter
  bleiben im eingeklappten Zustand sichtbar (Icon-only).

### Behoben

- **☰ Sidebar-Burger** — Icon fehlte. Burger-Button nutzt jetzt `QToolButton` mit Theme-Icon.
- **◀ Sidebar-Einklappen** — Logo und App-Titel wurden nicht ausgeblendet. Beim Aufklappen
  wurde fälschlicherweise in ein Turnier navigiert (nav-Signale nicht geblockt).
- **📝 Textboxen Beschreibung/Notizen** — Mehrzeilige Eingabefelder im Vereinsprofil zeigten
  nur eine Zeile. Fixe Höhe (90 px) wie die Textvorlagen-Boxen im Druck-Tab.

## [0.6.0] – 2026-10-20

### Hinzugefügt

- **🔄 Phasenwechsel rückwärts** — Neue Schaltfläche „← Vorherige Phase" (rot) im
  Sidebar-Navigator. Jeder Rückwärts-Wechsel wird als erzwungen im Protokoll festgehalten.
- **🌟 Erststart-Assistent** — Beim ersten App-Start ohne Vereinsname: überspringbarer
  Einrichtungsdialog für Vereinsname, Ort und Verband.
- **💾 Backup-Tab in Einstellungen** — Lokales ZIP-Backup (NAS/USB) mit konfigurierbarer
  Aufbewahrungsanzahl, Nextcloud-Upload per WebDAV sowie Wiederherstellung aus ZIP.
- **📊 Dashboard-Kacheln Regelwerke und Bogenklassen** — Klick navigiert direkt zur
  jeweiligen Ansicht.
- **📊 Turnier-Dashboard-Kacheln klickbar** — Teilnehmer-, Einnahmen-, Fortschritts- und
  Phasen-Kachel navigieren per Klick zur zugehörigen Ansicht.
- **👥 Vereinsvorstand-Kontakte** — Fünf Vorstandsrollen im Vereinsprofil hinterlegbar.
  Migration 0005 fügt zehn neue Spalten hinzu.
- **🧙 Turnier-Assistent Kontaktseite** — Dropdown zur Auswahl einer Vorstandsperson als
  Turnierkontakt.

### Geändert

- **◀ Sidebar resizierbar** — Per Maus (QSplitter) in der Breite veränderbar und über einen
  Burger-Button in einen Icon-Only-Modus kollabierbar.
- **🏹 App-Logo klickbar** — Klick navigiert zum Haupt-Dashboard.
- **🏁 Check-in-Verbesserungen** — „Als Walk-in erfassen" neben „Einchecken" (rot). Enter
  löst das Einchecken nicht mehr automatisch aus.
- **💶 Gebühren-Tab** — In den Phasen Schießen, Wertung und Abgeschlossen ausgeblendet.

### Behoben

- **💶 Einnahmen-Dashboard zeigt 0 €** — Wenn `fee_amount_paid` nicht gesetzt war, wurde
  fälschlich 0 € angezeigt. Jetzt wird auf den Betrag der zugewiesenen Startgebühr
  zurückgegriffen.

## [0.5.0] – 2026-10-19

### Hinzugefügt

- **🏢 Vereinsprofil erweitert** — Bankdaten (Kontoinhaber, IBAN, BIC, Verwendungszweck-Vorlage)
  und Parcours-Beschreibung als neue Felder.
- **⚙️ Einstellungen neu strukturiert** — Fünf Tabs: Vereinsprofil, Bankdaten, Design,
  Verhalten, Druck.
- **🏢 Vereinsname im Fenstertitel** — Titelleiste zeigt „BowTally – [Vereinsname]".
- **🏢 Vereinslogo auf beiden Dashboards** — Logo erscheint oben rechts im globalen Dashboard
  und im Turnier-Dashboard.
- **📊 Dashboard-Erweiterungen** — Aktive Turniere zeigen Auslastung als `(angemeldet/max)`.
  Schützen-Kachel zeigt Anzahl ohne Vereinszugehörigkeit.
- **🧙 Turnier-Assistent verbessert** — Reiter 1: Veranstalter und Ort aus dem Vereinsprofil
  übernehmen. Reiter 2: Regelwerksbeschreibung als formatierte Karte. Reiter 7: alle Bankdaten
  importierbar. Reiter 9: Trennlinien zwischen Abschnitten, einheitlicher Einzug (140 px).
- **📋 Leitfaden-Direktlinks** — „Turnier bearbeiten"-Knöpfe navigieren zu spezifischen
  Assistentenseiten.

## [0.4.0] – 2026-10-19

### Hinzugefügt

- **🔄 Turnierphasen** — Ausschreibung, Vorbereitung, Anmeldung, Einschreibung, Schießen,
  Auswertung, Abgeschlossen. Blocker und Warnungen je Phasenwechsel; Phasenwechsel-Protokoll.
- **🗂️ Turnier-Kontext** — Geöffnetes Turnier erscheint oben in der Seitenleiste mit
  Phasenliste, Knopf „Nächste Phase" und Protokoll. Wird beim nächsten Start wiederhergestellt.
- **📋 Leitfaden** — Je Phase mit Erklärung, Aufgaben und Direktlinks, Statusampeln und
  abhakbarer Checkliste.
- **📄 Ausschreibungs-PDF** — Aus Turnierdaten und Textvorlagen; Veraltet-Markierung nach
  Datenänderungen.
- **💶 Startgebühren** — Je Turnier, vorbelegt aus Vorlagen; zugewiesene Gebühren können nicht
  gelöscht werden.
- **✅ Anmelde- und Zahlungsstatus** — Je Teilnehmer, Status-Chips, Schnellaktionen per
  Rechtsklick, Sammelaktionen.
- **🔢 Maximale Teilnehmerzahl** — Auslastungsbalken; volle Turniere sperren Zuweisen,
  Import und Walk-ins.
- **🏁 Einschreibe-Ansicht** — Suche nach Name oder Startnummer, Einchecken per Enter,
  Warnung bei offener Zahlung, Walk-in-Erfassung, Einschreibeliste als PDF.
- **📊 Turnier-Dashboard** — Teilnehmer, Einnahmen, Ergebnisfortschritt, aktuelle Phase und
  nächste Aufgabe, Klassenübersicht und Zeitplan.
- **🧙 Turnier-Assistent erweitert** — Um vier Schritte: Fristen und Zeiten, Startgebühren,
  Kontakt und Bankdaten, Hinweise und Texte.
- **📤 Export aller Turnierdaten** — Teilnehmer, Ergebnisse, Rangliste und Gebühren.

### Geändert

- **🔄 Phase** ersetzt den bisherigen Status Entwurf/Aktiv/Abgeschlossen. Bestehende Turniere
  werden bei der Migration übernommen (Entwurf → Ausschreibung, Aktiv → Schießen).

### Behoben

- **🏁 Walk-in** — Check-in-Status wurde durch ein Neuladen des Datensatzes wieder
  überschrieben.

## [0.3.0] – 2026-10-19

### Hinzugefügt

- **🧩 Komponentenbibliothek** — Seitenpanel, Toasts, Status-Chips, Aktionsleiste,
  Leerzustände, Bestätigungsdialog, Suchfeld mit Verzögerung, Datentabelle.
- **⌨️ Ergebniseingabe per Tastatur** — Enter/↓/↑/Tab, Zonenliste beim Bearbeiten, eingefrorene
  Namens- und Summenspalten, Farbmarkierung für Top-Treffer und Fehlschüsse.
- **👥 Teilnehmerverwaltung** — Mehrfachauswahl, Bearbeitung direkt in der Tabelle,
  Sammelaktionen für Klasse und Gruppe.
- **🏆 Auswertung** — Podium Gold/Silber/Bronze, „ex aequo", PDF-Erstellung im Hintergrund,
  Export als Auswahlmenü.
- **⌨️ Globale Tastenkürzel** — `Strg+N`, `Strg+F`, `Strg+S`, `F5`, `F1`.

### Geändert

- Nicht-kritische Meldungen erscheinen als Hinweis (Toast) statt als Meldungsfenster.
- Löschen und andere unumkehrbare Aktionen fragen immer über einen Bestätigungsdialog nach.

### Behoben

- **🏹 Schütze speichern** — „(keine)" als Standardklasse verhinderte das Speichern.
- **🔽 Tabellensortierung** — Tabellen waren anfangs absteigend nach der ersten Spalte sortiert.
- **🎨 Farbige Zellen** — In Ergebniseingabe und Rangliste vom Stylesheet überdeckt.
- **⌨️ Ergebniseingabe** — Nach Enter in der Ergebniseingabe ging das nächste getippte Zeichen
  verloren.
- **⌨️ Ergebniseingabe** — Esc bei offener Zonenliste verschob den Fokus ins Suchfeld.

## [0.2.0] – 2026-10-18

### Hinzugefügt

- **🌙 Dunkler Modus** — Hell, dunkel oder wie Windows; umschaltbar in der Seitenleiste und
  in den Einstellungen. Dunkle Farben sind eigene, änderbare Einstellungen.
- **🔄 Farbige Statusanzeige** — Für Turniere im Turnierkopf und auf dem Dashboard.

### Geändert

- **🎨 Überarbeitetes Erscheinungsbild** — Neutrale Seitenleiste mit eigenen Linien-Icons,
  flache Tabellen, unterstrichene Reiter, abgerundete Eingabefelder und Knöpfe.
- **📦 Installer mit NSIS** — Statt Inno Setup. `build\build.bat` baut Anwendung und
  Installer in einem Schritt und verwendet automatisch das Projekt-venv.
- **🔢 Versionsverwaltung** — Einzige Quelle der Wahrheit: `bowtally/__version__.py`.

## [0.1.0] – 2026-10-18

### Hinzugefügt

- **🏹 Erste Version** — Schützen-Stammdaten, Regelwerke (IBO 3D, ASA 3D, WA 3D),
  Bogenklassen, Turnier-Assistent, Teilnehmerverwaltung, Ergebniseingabe, Ranglisten mit
  Tie-Break, druckfertige Ergebnisliste als PDF, Import/Export CSV/XLSX/ODS, Einstellungen
  mit Vereinsprofil und Farbschema. SQLite-Datenbank mit Alembic-Migrationen, Build mit
  PyInstaller.

[Unveröffentlicht]: https://github.com/jenskaesler/bowtally/compare/v2026.11.4...HEAD
[2026.11.4]: https://github.com/jenskaesler/bowtally/compare/v2026.11.3...v2026.11.4
[2026.11.1]: https://github.com/jenskaesler/bowtally/compare/v2026.10.9...v2026.11.1
[2026.10.9]: https://github.com/jenskaesler/bowtally/compare/v2026.10.7...v2026.10.9
[2026.10.7]: https://github.com/jenskaesler/bowtally/compare/v2026.10.6...v2026.10.7
[2026.10.6]: https://github.com/jenskaesler/bowtally/compare/v2026.10.4...v2026.10.6
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
