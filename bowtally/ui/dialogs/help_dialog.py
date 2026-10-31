# -*- coding: utf-8 -*-
"""App-Hilfe Dialog: Inhaltsverzeichnis + HTML-Ansicht."""
from PySide6.QtWidgets import (QDialog, QFrame, QHBoxLayout, QLineEdit, QListWidget,
                                QTextBrowser, QVBoxLayout, QWidget)

from bowtally.ui import button, restore_geom, save_geom, theme

_SECTIONS = [
    ("Übersicht", """
<h2>BowTally – Übersicht</h2>
<p>BowTally ist eine Turnierverwaltungs-App für 3D-Bogensport-Vereine. Die wichtigsten Module:</p>
<ul>
  <li><b>Turniere</b> – anlegen, bearbeiten, phasenweise durchführen</li>
  <li><b>Schützen</b> – Stammdaten und Einschreibung</li>
  <li><b>Ergebnisse</b> – Punkteingabe und Ranglistenberechnung</li>
  <li><b>Regelwerke &amp; Klassen</b> – Punktverteilung und Wertungsgruppen</li>
  <li><b>Einstellungen</b> – Vereinsprofil, Design, Druck und Verhalten</li>
</ul>
<h3>Navigation</h3>
<p>Links in der Seitenleiste wechselst du zwischen den Modulen.
Ist ein Turnier geöffnet, erscheinen im oberen Teil der Leiste
turnierspezifische Schnellzugriffe.</p>
<h3>Leitfaden</h3>
<p>Für jedes geöffnete Turnier zeigt der <b>Leitfaden</b> in der Seitenleiste
alle anstehenden Aufgaben an. Ein Klick auf eine Aufgabe springt direkt
in die entsprechende Ansicht.</p>
"""),
    ("Turniere", """
<h2>Turniere</h2>
<h3>Turnier anlegen</h3>
<p>Über <b>Neu</b> (Strg+N) öffnet sich der Turnier-Assistent. Er führt durch
acht Schritte: Basisdaten, Regelwerk, Bogenklassen, Konfiguration, Fristen,
Gebühren, Kontakt/Bank und Texte.</p>
<h3>Turnierphasen</h3>
<ol>
  <li><b>Entwurf</b> – Vorbereitung, noch nicht aktiv</li>
  <li><b>Ausschreibung</b> – Turnier ist öffentlich angekündigt</li>
  <li><b>Anmeldung</b> – Schützen können sich anmelden</li>
  <li><b>Einschreibung</b> – Vor-Ort-Check-in am Turniertag</li>
  <li><b>Schießen</b> – Ergebniseingabe aktiv</li>
  <li><b>Abgeschlossen</b> – Turnier beendet, Rangliste eingefroren</li>
</ol>
<p>Mit dem <b>Nächste Phase</b>-Button in der Seitenleiste wechselst du in die
nächste Phase. BowTally prüft dabei Voraussetzungen (z. B. mindestens ein
Teilnehmer).</p>
<h3>Warteliste</h3>
<p>Ist <i>Warteliste bei Vollbelegung</i> auf <b>Automatisch</b> eingestellt,
werden überzählige Anmeldungen automatisch auf die Warteliste gesetzt
(Status „Auf Warteliste").</p>
<h3>Turnier kopieren</h3>
<p>Ein Turnier kann als Vorlage kopiert werden (ohne Teilnehmer und Ergebnisse).
Nützlich für wiederkehrende Turniere.</p>
"""),
    ("Schützen & Teilnehmer", """
<h2>Schützen &amp; Teilnehmer</h2>
<h3>Schützen-Stammdaten</h3>
<p>Im Modul <b>Schützen</b> verwaltest du die Stammdaten aller Vereinsmitglieder.
Über <b>Importieren</b> lassen sich Schützenlisten als CSV oder Excel einlesen –
BowTally erkennt gängige Spaltenbezeichnungen automatisch.</p>
<p>Schützen können als <b>inaktiv</b> markiert werden und werden dann aus
Auswahllisten ausgeblendet. Die Checkbox <i>Inaktive Schützen anzeigen</i>
blendet sie wieder ein.</p>
<h3>Teilnehmer-Anmeldung</h3>
<p>Im Turnier unter <b>Teilnehmer</b> weist du Schützen über <b>Schütze zuweisen</b>
dem Turnier zu. Bei mehreren Schützen kannst du die Bogenklassen im
folgenden Dialog individuell anpassen.</p>
<h3>Anmeldestatus</h3>
<table border="0" cellspacing="0" cellpadding="5" style="border-collapse:collapse;">
  <tr><td><b>Gemeldet</b></td><td>Anmeldung eingegangen, noch nicht bestätigt</td></tr>
  <tr><td><b>Bestätigt</b></td><td>Anmeldung vom Veranstalter bestätigt</td></tr>
  <tr><td><b>Eingecheckt</b></td><td>Teilnehmer vor Ort eingecheckt</td></tr>
  <tr><td><b>Auf Warteliste</b></td><td>Turnier war voll, automatisch auf Warteliste</td></tr>
  <tr><td><b>DNS</b></td><td>Nicht gestartet (Did Not Start)</td></tr>
  <tr><td><b>Zurückgezogen</b></td><td>Anmeldung zurückgezogen</td></tr>
  <tr><td><b>DSQ</b></td><td>Disqualifiziert</td></tr>
</table>
<h3>Gebühren &amp; Zahlung</h3>
<p>Startgebühren werden im Tab <b>Startgebühren</b> angelegt und können
Teilnehmern direkt in der Tabelle zugewiesen werden. Zahlungsstatus
(Offen / Ausstehend / Bezahlt) wird ebenfalls hier verwaltet.</p>
<h3>Inline-Bearbeitung</h3>
<p>Doppelklick auf Startnummer, Bogenklasse, Startgruppe, Gebühr oder
Startzeit bearbeitet die Felder direkt in der Tabelle.</p>
"""),
    ("Parcours, Zeitplan & Preise", """
<h2>Parcours, Zeitplan &amp; Preise</h2>
<h3>Parcours-Planung</h3>
<p>Der Tab <b>Parcours</b> (ab Phase <i>Planung</i>) enthält alle Scheiben bzw. 3D-Tiere.
Felder: Scheiben-Nr., Tier / Bezeichnung, Distanz (m), Pfeilstoppklasse, Geländetyp,
Max. Gruppengröße und Helfernotiz.</p>
<p>Über <b>Aus Inventar …</b> im Bearbeitungsdialog lassen sich Bezeichnungen direkt
aus dem Vereinsinventar übernehmen. Die Reihenfolge ist per <b>Drag-and-Drop</b>
änderbar und wird dauerhaft gespeichert.</p>
<p>Drucken: <b>Aufbauplan</b> (mit Helfernotizen für Helfer) und <b>Scheibenplan</b>
(ohne Notizen für Teilnehmer) als PDF.</p>
<h3>Zeitplan</h3>
<p>Der Tab <b>Zeitplan</b> erscheint ab Phase <i>Planung</i>, sofern kein Lossystem
aktiviert ist. Hier werden Startgruppen und -zeiten verwaltet.</p>
<h3>Lossystem (Auslosung)</h3>
<p>Wird im Turnier-Assistenten unter <i>Konfiguration</i> das <b>Lossystem</b>
aktiviert, ersetzt die Auslosung den Zeitplan. Der Button <b>Auslosung …</b>
im Teilnehmer-Tab verteilt Teilnehmer zufällig auf Gruppen. Die maximalen
Gruppengrößen aus dem Parcours werden dabei berücksichtigt.</p>
<h3>Preise</h3>
<p>Der Tab <b>Preise</b> ist immer sichtbar und enthält die Preisgestaltung des Turniers.</p>
<h3>Wertungsblätter</h3>
<p>Unter <b>Wertungsblätter</b> werden Vorlagen für das Drucken von Scorebögen verwaltet.</p>
"""),
    ("Inventar & Kalender", """
<h2>Inventar &amp; Kalender</h2>
<h3>Vereinsinventar</h3>
<p>Das Modul <b>Inventar</b> (Seitenleiste) verwaltet Scheiben (Scheibenbilder)
und 3D-Ziele des Vereins. Felder: Bezeichnung, Hersteller, Anzahl, Zustand
(Gut / Mittel / Schlecht) und ob der Eintrag aktiv ist.</p>
<p>Aktive Einträge erscheinen im Parcours-Dialog unter <b>Aus Inventar …</b>,
um Scheibenbezeichnungen schnell zu übernehmen.</p>
<h3>Jahresansicht im Kalender</h3>
<p>Der Kalender wechselt mit dem <b>Jahres-Button</b> in eine Übersicht
aller zwölf Monate. Tage mit Turnieren sind farblich hervorgehoben.
Ein Klick auf einen Monatsnamen springt direkt in die Monatsansicht.</p>
<h3>Regelwerk-Standard</h3>
<p>In der Liste der Regelwerke lässt sich über <b>Als Standard setzen</b>
(Rechtsklick → Kontextmenü) ein Regelwerk als Standard markieren (⭐).
Beim Anlegen neuer Turniere wird dieses Regelwerk automatisch vorausgewählt.</p>
"""),
    ("Ergebnisse & Wertung", """
<h2>Ergebnisse &amp; Wertung</h2>
<h3>Ergebniseingabe</h3>
<p>In der Schieß-Phase können Punkte je Scheibe direkt eingegeben werden.
Navigiere mit <b>Tab / Umschalt+Tab</b> zwischen Scheiben und
mit <b>Enter / ↓ / ↑</b> zwischen Teilnehmern.</p>
<h3>Rang berechnen</h3>
<p>Der Rang wird nach jeder Eingabe automatisch neu berechnet (konfigurierbar
unter Einstellungen → Verhalten). Bei Punktgleichstand greift die
konfigurierte Tie-Break-Logik.</p>
<h3>Tie-Break-Logik</h3>
<ul>
  <li><b>Meiste Top-Treffer</b> – Wer mehr Treffer in der höchsten Zone hat, gewinnt</li>
  <li><b>Gesamthöchste Wertung</b> – Höchste Einzelscheibenwertung entscheidet</li>
</ul>
<h3>Exportieren</h3>
<p>Ranglisten und Einschreibelisten können als CSV, Excel oder OpenDocument exportiert werden.</p>
"""),
    ("Einstellungen & Stammdaten", """
<h2>Einstellungen &amp; Stammdaten</h2>
<h3>Vereinsprofil</h3>
<p>Vereinsname, Adresse, Kontaktdaten und Logo. Diese Daten erscheinen auf
Ausschreibungen und Urkunden. Unter <b>Standard-Kontaktperson</b> legst du
fest, welche Vorstand-Rolle beim Erstellen neuer Turniere vorbelegt wird.</p>
<h3>Vereinsvorstand</h3>
<p>Vorname, Nachname, Telefon und E-Mail je Vorstandsrolle. Im Turnier-Assistenten
können diese Daten per Klick auf <b>Übernehmen</b> als Turnierkontakt übernommen werden.</p>
<h3>Bankdaten</h3>
<p>IBAN, BIC und Verwendungszweck-Vorlage für Startgebühren-Überweisungen.
Im Verwendungszweck können Platzhalter genutzt werden (z. B. <code>{name}</code>).</p>
<h3>Design</h3>
<p>Hell/Dunkel-Modus und individuelle Farbanpassung für helles und dunkles Theme.</p>
<h3>Verhalten</h3>
<p>Sprache, Schriftart, Rang-Neuberechnung und Tie-Break-Logik.</p>
<h3>Druck</h3>
<p>Papiergröße, Ausrichtung, Logo auf Ausdrucken und Textvorlagen für Ausschreibungen.</p>
<h3>Regelwerke</h3>
<p>Regelwerke definieren, wie viele Schüsse je Scheibe erlaubt sind und
wie viele Punkte je Trefferzone vergeben werden. Standard-Regelwerke
(Chip <i>Standard</i>) sind schreibgeschützt – über <b>Kopieren</b> erstellst
du eine anpassbare Kopie.</p>
<h3>Bogenklassen</h3>
<p>Bogenklassen gruppieren Schützen für die Wertung (z. B. Recurve, Compound).
Auch Standard-Klassen sind schreibgeschützt. Reihenfolge per Drag-and-Drop.</p>
<h3>Backup</h3>
<p>Aktiviere <i>Backup beim Beenden</i> unter Einstellungen → Backup für
automatische Sicherungen. Zur Wiederherstellung: <b>Backup wiederherstellen</b>
→ ZIP-Datei wählen. <b>Achtung:</b> Die aktuelle Datenbank wird unwiderruflich
ersetzt – App danach neu starten.</p>
<h3>Navigation</h3>
<p>Unter Einstellungen → <b>Navigation</b> lässt sich die Reihenfolge der
Einträge in der Seitenleiste per Drag-and-Drop anpassen. Die Änderungen
werden nach einem <b>Neustart</b> der App wirksam.</p>
"""),
    ("Rechtsklick-Menüs", """
<h2>Rechtsklick-Menüs</h2>
<p>In allen Listen öffnet ein Rechtsklick auf eine Zeile ein Kontextmenü
mit den verfügbaren Aktionen für den ausgewählten Eintrag.</p>
<h3>Turnierliste</h3>
<table border="0" cellspacing="0" cellpadding="5" style="border-collapse:collapse;">
  <tr><td><b>Turnier öffnen</b></td><td>Als aktives Turnier öffnen</td></tr>
  <tr><td><b>Bearbeiten</b></td><td>Im Assistenten bearbeiten (gesperrt ab Einschreibungsphase)</td></tr>
  <tr><td><b>Kopieren</b></td><td>Als Vorlage kopieren (ohne Teilnehmer)</td></tr>
  <tr><td><b>Löschen</b></td><td>Turnier mit allen Daten löschen</td></tr>
</table>
<h3>Schützenliste</h3>
<table border="0" cellspacing="0" cellpadding="5" style="border-collapse:collapse;">
  <tr><td><b>Bearbeiten</b></td><td>Stammdaten im Seitenpanel bearbeiten</td></tr>
  <tr><td><b>Kopieren</b></td><td>Schützen-Datensatz duplizieren</td></tr>
  <tr><td><b>Als inaktiv markieren</b></td><td>Aus Auswahllisten ausblenden</td></tr>
  <tr><td><b>Löschen</b></td><td>Schützen dauerhaft löschen</td></tr>
</table>
<h3>Regelwerke &amp; Bogenklassen</h3>
<table border="0" cellspacing="0" cellpadding="5" style="border-collapse:collapse;">
  <tr><td><b>Bearbeiten</b></td><td>Im Seitenpanel bearbeiten (Standard-Einträge schreibgeschützt)</td></tr>
  <tr><td><b>Kopieren</b></td><td>Anpassbare Kopie anlegen</td></tr>
  <tr><td><b>Löschen</b></td><td>Eintrag löschen (Standard-Einträge schreibgeschützt)</td></tr>
</table>
<h3>Teilnehmerliste</h3>
<p>Aktionen werden je nach Turnierstatus und aktuellem Anmeldestatus ein- oder
ausgeblendet. Bei abgeschlossenen Turnieren sind alle Aktionen gesperrt.</p>
<table border="0" cellspacing="0" cellpadding="5" style="border-collapse:collapse;">
  <tr><td><b>Anmeldung bestätigen</b></td><td>Nur für „Gemeldet" oder „Auf Warteliste"</td></tr>
  <tr><td><b>Zahlung als eingegangen markieren</b></td><td>Nur wenn Gebühr hinterlegt und noch nicht bezahlt</td></tr>
  <tr><td><b>Einchecken</b></td><td>Nur in der Einschreibungs- oder Schieß-Phase</td></tr>
  <tr><td><b>Als DNS markieren</b></td><td>Nur für aktive Teilnehmer (Gemeldet/Bestätigt/Eingecheckt)</td></tr>
  <tr><td><b>Als zurückgezogen markieren</b></td><td>Nur für aktive Teilnehmer</td></tr>
  <tr><td><b>Auf „Gemeldet" zurücksetzen</b></td><td>Nur wenn bereits bestätigt oder eingecheckt</td></tr>
  <tr><td><b>Zahlung als ausstehend markieren</b></td><td>Zahlungsstatus auf „Ausstehend" setzen</td></tr>
  <tr><td><b>Gebühr / Klasse / Gruppe zuweisen</b></td><td>Direkte Zuweisung für die Auswahl</td></tr>
  <tr><td><b>Entfernen</b></td><td>Teilnehmer aus dem Turnier entfernen</td></tr>
</table>
"""),
    ("Referenz", """
<h2>Referenz</h2>
<h3>Platzhalter</h3>
<p>Platzhalter werden in bestimmten Textfeldern durch echte Werte ersetzt.
Schreibe sie immer in geschweiften Klammern: <code>{platzhalter}</code></p>
<p><b>Verwendungszweck (Bankverbindung):</b></p>
<table border="0" cellspacing="0" cellpadding="5" style="border-collapse:collapse;">
  <tr><td><code>{name}</code></td><td>Vor- und Nachname des Schützen</td></tr>
  <tr><td><code>{bow_class}</code></td><td>Bogenklasse des Schützen</td></tr>
</table>
<p><i>Beispiel:</i> <code>3D Turnier 2027, {name}, {bow_class}</code></p>
<p><b>E-Mail-Vorlagen</b> – verfügbare Platzhalter:</p>
<p><i>Immer verfügbar:</i></p>
<table border="0" cellspacing="0" cellpadding="4" style="border-collapse:collapse;">
  <tr><td><code>{name}</code></td><td>Vor- und Nachname des Teilnehmers / Helfers</td></tr>
  <tr><td><code>{turniername}</code></td><td>Name des Turniers</td></tr>
  <tr><td><code>{datum}</code></td><td>Turnierdatum (TT.MM.JJJJ)</td></tr>
  <tr><td><code>{ort}</code></td><td>Veranstaltungsort des Turniers</td></tr>
  <tr><td><code>{anmeldefrist}</code></td><td>Anmeldefrist (TT.MM.JJJJ)</td></tr>
  <tr><td><code>{iban}</code></td><td>IBAN aus den Turnier-Bankdaten</td></tr>
  <tr><td><code>{vereinsname}</code></td><td>Vereinsname aus dem Vereinsprofil</td></tr>
  <tr><td><code>{kontakt_name}</code></td><td>Name der Standard-Kontaktperson</td></tr>
  <tr><td><code>{kontakt_email}</code></td><td>E-Mail der Standard-Kontaktperson</td></tr>
  <tr><td><code>{kontakt_telefon}</code></td><td>Telefon der Standard-Kontaktperson</td></tr>
</table>
<p><i>Nur in Teilnehmer-Vorlagen:</i></p>
<table border="0" cellspacing="0" cellpadding="4" style="border-collapse:collapse;">
  <tr><td><code>{verein}</code></td><td>Vereinsname des Teilnehmers</td></tr>
  <tr><td><code>{klasse}</code></td><td>Bogenklasse des Teilnehmers</td></tr>
  <tr><td><code>{startnummer}</code></td><td>Zugewiesene Startnummer</td></tr>
  <tr><td><code>{startgruppe}</code></td><td>Startgruppe (z.B. Gruppe A)</td></tr>
  <tr><td><code>{startzeit}</code></td><td>Geplante Startzeit</td></tr>
  <tr><td><code>{verwendungszweck}</code></td><td>Zahlungsreferenz aus der Verwendungszweck-Vorlage</td></tr>
  <tr><td><code>{freigewordene_plaetze}</code></td><td>Freigewordene Plätze <i>(nur Wartelistenvorlage)</i></td></tr>
  <tr><td><code>{platz}</code></td><td>Endrang <i>(nur Ergebnisvorlage)</i></td></tr>
  <tr><td><code>{punkte}</code></td><td>Gesamtpunktzahl <i>(nur Ergebnisvorlage)</i></td></tr>
</table>
<p><i>Nur in der Helfer-Vorlage:</i></p>
<table border="0" cellspacing="0" cellpadding="4" style="border-collapse:collapse;">
  <tr><td><code>{aufgabe}</code></td><td>Zugewiesene Aufgabe des Helfers</td></tr>
  <tr><td><code>{von}</code></td><td>Einsatzbeginn</td></tr>
  <tr><td><code>{bis}</code></td><td>Einsatzende</td></tr>
</table>
<h3>Tastenkürzel</h3>
<table border="0" cellspacing="0" cellpadding="5" style="border-collapse:collapse;">
  <tr><td><code>Strg+N</code></td><td>Neu (Schütze, Klasse, Regelwerk, Turnier, Teilnehmer)</td></tr>
  <tr><td><code>Strg+F</code></td><td>Suchfeld der aktuellen Ansicht</td></tr>
  <tr><td><code>Strg+S</code></td><td>Speichern (Seitenpanel, Ergebniseingabe)</td></tr>
  <tr><td><code>Esc</code></td><td>Seitenpanel schließen / Suche leeren / Eingabe verwerfen</td></tr>
  <tr><td><code>F5</code></td><td>Ansicht neu laden</td></tr>
  <tr><td><code>F1</code></td><td>Diese Hilfe</td></tr>
  <tr><td><code>Enter</code></td><td>Ausgewählten Eintrag öffnen / Seitenpanel speichern / Einchecken</td></tr>
  <tr><td><code>Tab / Umschalt+Tab</code></td><td>Ergebniseingabe: nächste / vorherige Scheibe</td></tr>
  <tr><td><code>Enter / ↓ / ↑</code></td><td>Ergebniseingabe: nächster / vorheriger Teilnehmer</td></tr>
</table>
<h3>Backup &amp; Wiederherstellung</h3>
<p>Aktiviere <i>Backup beim Beenden der App erstellen</i> unter Einstellungen → Backup.
Für manuelle Sicherungen: <b>Backup jetzt erstellen</b> (lokal) oder
<b>Zu Nextcloud sichern</b>.</p>
<p>Zur Wiederherstellung: <b>Backup wiederherstellen</b> → ZIP-Datei wählen.
<b>Achtung:</b> Die aktuelle Datenbank wird unwiderruflich ersetzt.
App danach neu starten.</p>
"""),
]


def _prepare_html(html: str) -> str:
    html = html.replace(' style="background:#f0f4f8;"', '')
    # Insert <hr> before every <h3> except the first
    parts = html.split('<h3>')
    if len(parts) > 1:
        html = parts[0] + '<h3>' + '<hr><h3>'.join(parts[1:])
    return html


class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("App-Hilfe")
        self.resize(960, 680)
        restore_geom(self, "help")
        self.finished.connect(lambda: save_geom(self, "help"))

        # Sidebar
        sidebar = QWidget()
        sidebar.setFixedWidth(220)
        sidebar_lay = QVBoxLayout(sidebar)
        sidebar_lay.setContentsMargins(8, 8, 8, 8)
        sidebar_lay.setSpacing(6)

        self._help_search = QLineEdit()
        self._help_search.setPlaceholderText("Suchen …")
        self._help_search.setClearButtonEnabled(True)
        sidebar_lay.addWidget(self._help_search)

        self._nav = QListWidget()
        self._nav.setObjectName("helpNav")
        for title, _ in _SECTIONS:
            self._nav.addItem(title)
        sidebar_lay.addWidget(self._nav, 1)

        vline = QFrame()
        vline.setFrameShape(QFrame.Shape.VLine)
        vline.setFrameShadow(QFrame.Shadow.Sunken)

        self._browser = QTextBrowser()
        self._browser.setOpenExternalLinks(True)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(sidebar)
        body.addWidget(vline)
        body.addWidget(self._browser, 1)

        self._nav.currentRowChanged.connect(self._show_section)
        self._help_search.textChanged.connect(self._filter_help)
        self._nav.setCurrentRow(0)
        self._apply_browser_css()
        theme.notifier.changed.connect(self._apply_browser_css)

        close_row = QHBoxLayout()
        close_row.addStretch()
        close_row.addWidget(button("Schließen", self.accept, "primary"))

        lay = QVBoxLayout(self)
        lay.addLayout(body, 1)
        lay.addLayout(close_row)

    def _filter_help(self, text: str):
        text = text.strip().lower()
        for i in range(self._nav.count()):
            item = self._nav.item(i)
            if not text:
                item.setHidden(False)
            else:
                title, content = _SECTIONS[i]
                visible = text in title.lower() or text in content.lower()
                item.setHidden(not visible)

    def _apply_browser_css(self):
        t = theme.current()
        css = (f"code {{ background: {t['surface']}; border-radius: 3px; "
               f"padding: 1px 4px; font-family: monospace; }}"
               f" h3 {{ border-bottom: 2px solid {t['primary']}; "
               f"padding-bottom: 5px; margin-top: 20px; font-size: 108%; }}"
               f" hr {{ border: none; border-top: 1px solid {t['border']}; "
               f"margin: 4px 0 14px 0; }}")
        self._browser.document().setDefaultStyleSheet(css)
        row = self._nav.currentRow()
        if row >= 0:
            self._browser.setHtml(_prepare_html(_SECTIONS[row][1]))

    def _show_section(self, row: int):
        if 0 <= row < len(_SECTIONS):
            self._browser.setHtml(_prepare_html(_SECTIONS[row][1]))
            self._browser.verticalScrollBar().setValue(0)

    def show_section(self, title: str):
        for i, (t, _) in enumerate(_SECTIONS):
            if t == title:
                self._nav.setCurrentRow(i)
                break
