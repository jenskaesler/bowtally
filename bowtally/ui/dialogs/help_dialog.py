# -*- coding: utf-8 -*-
"""App-Hilfe Dialog: Inhaltsverzeichnis + HTML-Ansicht."""
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QTabWidget, QTextBrowser, QVBoxLayout)

from bowtally.ui import button, theme

_SECTIONS = [
    ("Übersicht", """
<h2>BowTally – Übersicht</h2>
<p>BowTally ist eine Turnierverwaltungs-App für 3D-Bogensport-Vereine. Die wichtigsten Module:</p>
<ul>
  <li><b>Turniere</b> – anlegen, bearbeiten, phasenweise durchführen</li>
  <li><b>Schützen</b> – Teilnehmerverwaltung und Einschreibung</li>
  <li><b>Ergebnisse</b> – Punkteingabe und Ranglistenberechnung</li>
  <li><b>Regelwerke</b> – Punktverteilung je Trefferzone definieren</li>
  <li><b>Bogenklassen</b> – Klassen für Wertungsgruppen festlegen</li>
  <li><b>Einstellungen</b> – Vereinsprofil, Design, Druck und Verhalten</li>
</ul>
<h3>Navigation</h3>
<p>Links in der Seitenleiste wechselst du zwischen den Modulen.
Ist ein Turnier geöffnet, erscheinen im oberen Teil der Leiste
turnierspezifische Schnellzugriffe.</p>
"""),
    ("Turniere", """
<h2>Turniere</h2>
<h3>Turnier anlegen</h3>
<p>Über <b>Neu</b> (Strg+N) öffnet sich der Turnier-Assistent. Er führt dich durch
acht Schritte: Basisdaten, Regelwerk, Bogenklassen, Konfiguration, Fristen, Gebühren,
Kontakt/Bank und Texte.</p>
<h3>Turnierphasen</h3>
<ol>
  <li><b>Entwurf</b> – Turnier wird vorbereitet, noch nicht aktiv</li>
  <li><b>Anmeldung</b> – Schützen können sich anmelden</li>
  <li><b>Einschreibung</b> – Vor-Ort-Check-in am Turniertag</li>
  <li><b>Schießen</b> – Ergebniseingabe aktiv</li>
  <li><b>Abgeschlossen</b> – Turnier ist beendet, Rangliste eingefroren</li>
</ol>
<p>Mit dem <b>Nächste Phase</b>-Button in der Seitenleiste wechselst du in die nächste Phase.
BowTally prüft dabei Voraussetzungen (z. B. mindestens ein Teilnehmer).</p>
<h3>Turnier kopieren</h3>
<p>Ein Turnier kann als Vorlage kopiert werden (ohne Teilnehmer und Ergebnisse).
Nützlich für wiederkehrende Turniere.</p>
"""),
    ("Schützen", """
<h2>Schützen</h2>
<p>Im Modul <b>Schützen</b> verwaltest du die Stammdaten aller Schützen des Vereins.
Schützen können dann als Teilnehmer für Turniere angemeldet werden.</p>
<h3>Importieren</h3>
<p>Über <b>Importieren</b> lassen sich Schützenlisten als CSV- oder Excel-Datei einlesen.
BowTally erkennt gängige Spaltenbezeichnungen automatisch.</p>
<h3>Status</h3>
<p>Schützen können als <b>inaktiv</b> markiert werden. Inaktive Schützen werden
standardmäßig ausgeblendet (Filter „Inaktive anzeigen").</p>
"""),
    ("Ergebnisse & Rangliste", """
<h2>Ergebnisse &amp; Rangliste</h2>
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
<p>Ranglisten und Einschreibe-Listen können als CSV, Excel oder OpenDocument exportiert werden.</p>
"""),
    ("Regelwerke & Bogenklassen", """
<h2>Regelwerke &amp; Bogenklassen</h2>
<h3>Regelwerke</h3>
<p>Regelwerke definieren, wie viele Schüsse je Scheibe erlaubt sind und
wie viele Punkte je Trefferzone vergeben werden.</p>
<p>Standard-Regelwerke (mit dem Chip <i>Standard</i>) sind schreibgeschützt.
Um ein Regelwerk anzupassen, kopiere es zuerst über <b>Kopieren</b>.</p>
<h3>Bogenklassen</h3>
<p>Bogenklassen gruppieren Schützen für die Wertung (z. B. Recurve, Compound, Blankbogen).
Auch hier sind Standard-Klassen schreibgeschützt und müssen vor Änderungen kopiert werden.</p>
"""),
    ("Einstellungen", """
<h2>Einstellungen</h2>
<h3>Vereinsprofil</h3>
<p>Vereinsname, Adresse, Kontaktdaten und Logo des Vereins. Diese Daten erscheinen
auf Ausschreibungen und Urkunden.</p>
<p>Unter <b>Standard-Kontaktperson</b> legst du fest, welche Vorstand-Rolle beim
Erstellen neuer Turniere als Kontakt vorbelegt wird.</p>
<h3>Vereinsvorstand</h3>
<p>Vorname, Nachname, Telefon und E-Mail je Vorstandsrolle. Die hier gespeicherten
Daten können im Turnier-Assistenten per Klick auf <b>Übernehmen</b> als Turnierkontakt übernommen werden.</p>
<h3>Bankdaten</h3>
<p>IBAN, BIC und Verwendungszweck-Vorlage für Startgebühren-Überweisungen.
Im Verwendungszweck können Platzhalter genutzt werden (siehe <i>Platzhalter-Referenz</i>).</p>
<h3>Design</h3>
<p>Hell/Dunkel-Modus und individuelle Farbanpassung für Markenfarben, helles und dunkles Theme.</p>
<h3>Verhalten</h3>
<p>Sprache, Schriftart, Rang-Neuberechnung und Tie-Break-Logik.</p>
<h3>Druck</h3>
<p>Papiergröße, Ausrichtung (Format), Logo auf Ausdrucken und Textvorlagen für Ausschreibungen.</p>
<h3>Backup</h3>
<p>Automatisches Backup beim Beenden, lokales Backup auf NAS/USB und Nextcloud-Backup.</p>
"""),
    ("Platzhalter-Referenz", """
<h2>Platzhalter-Referenz</h2>
<p>Platzhalter werden in bestimmten Textfeldern durch echte Werte ersetzt.
Schreibe sie immer in geschweiften Klammern: <code>{platzhalter}</code></p>
<h3>Verwendungszweck (Bankverbindung)</h3>
<table border="0" cellspacing="0" cellpadding="6" style="border-collapse:collapse;">
  <tr style="background:#f0f4f8;">
    <th align="left" style="padding:6px 16px 6px 0;">Platzhalter</th>
    <th align="left">Beschreibung</th>
  </tr>
  <tr><td><code>{name}</code></td><td>Vor- und Nachname des Schützen</td></tr>
  <tr style="background:#f0f4f8;"><td><code>{bow_class}</code></td><td>Bogenklasse des Schützen</td></tr>
</table>
<p><i>Beispiel:</i> <code>3D Turnier 2027, {name}, {bow_class}</code></p>
<h3>Ausschreibungs-Texte</h3>
<p>In den Textvorlagen (Einstellungen → Druck → Textvorlagen) sind aktuell
keine variablen Platzhalter vorgesehen. Die Texte werden direkt übernommen.</p>
<h3>Hinweise zum Parcours (Turnier-Assistent)</h3>
<p>Im Turnier-Assistenten kann die Parcours-Beschreibung aus dem Vereinsprofil
über den Button <b>Aus Stammdaten</b> übernommen werden.</p>
"""),
    ("Tastenkürzel", """
<h2>Tastenkürzel</h2>
<table border="0" cellspacing="0" cellpadding="6" style="border-collapse:collapse;">
  <tr style="background:#f0f4f8;">
    <th align="left" style="padding:6px 16px 6px 0;">Taste</th>
    <th align="left">Funktion</th>
  </tr>
  <tr><td><code>Strg+N</code></td><td>Neu (Schütze, Klasse, Regelwerk, Turnier, Teilnehmer, Walk-in, Gebühr)</td></tr>
  <tr style="background:#f0f4f8;"><td><code>Strg+F</code></td><td>Suchfeld der aktuellen Ansicht</td></tr>
  <tr><td><code>Strg+S</code></td><td>Speichern (Seitenpanel, Ergebniseingabe)</td></tr>
  <tr style="background:#f0f4f8;"><td><code>Esc</code></td><td>Seitenpanel schließen / Suche leeren / Eingabe verwerfen</td></tr>
  <tr><td><code>F5</code></td><td>Ansicht neu laden</td></tr>
  <tr style="background:#f0f4f8;"><td><code>F1</code></td><td>Diese Hilfe</td></tr>
  <tr><td><code>Enter</code></td><td>Ausgewählten Eintrag öffnen / Seitenpanel speichern / Einchecken</td></tr>
  <tr style="background:#f0f4f8;"><td><code>Tab / Umschalt+Tab</code></td><td>Ergebniseingabe: nächste / vorherige Scheibe</td></tr>
  <tr><td><code>Enter / ↓ / ↑</code></td><td>Ergebniseingabe: nächster / vorheriger Teilnehmer</td></tr>
</table>
"""),
    ("Backup & Wiederherstellung", """
<h2>Backup &amp; Wiederherstellung</h2>
<h3>Automatisches Backup</h3>
<p>Aktiviere <i>Backup beim Beenden der App erstellen</i> unter Einstellungen → Backup,
damit beim Schließen der App automatisch ein ZIP-Backup erstellt wird.</p>
<h3>Lokales Backup</h3>
<p>Wähle einen Pfad auf einem NAS, USB-Laufwerk oder einem lokalen Ordner.
Über <b>Backup jetzt erstellen</b> kannst du jederzeit manuell sichern.
Die Aufbewahrungsanzahl bestimmt, wie viele alte Backups behalten werden.</p>
<h3>Nextcloud</h3>
<p>Gib URL, Benutzername und Passwort deiner Nextcloud-Instanz ein und
sichere mit <b>Zu Nextcloud sichern</b>.</p>
<h3>Wiederherstellen</h3>
<p>Über <b>Backup wiederherstellen</b> wählst du eine lokale ZIP-Datei aus.
<b>Achtung:</b> Die aktuelle Datenbank wird dabei unwiderruflich ersetzt.
Starte die App danach neu.</p>
"""),
]


class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("App-Hilfe")
        self.resize(860, 620)

        self._tabs = QTabWidget()
        self._browsers: list[QTextBrowser] = []
        for title, _ in _SECTIONS:
            browser = QTextBrowser()
            browser.setOpenExternalLinks(True)
            self._browsers.append(browser)
            self._tabs.addTab(browser, title)

        self._apply_browser_css()
        theme.notifier.changed.connect(self._apply_browser_css)

        close_row = QHBoxLayout()
        close_row.addStretch()
        close_row.addWidget(button("Schließen", self.accept, "primary"))

        lay = QVBoxLayout(self)
        lay.addWidget(self._tabs)
        lay.addLayout(close_row)

    def _apply_browser_css(self):
        t = theme.current()
        css = (f"code {{ background: {t['surface']}; border-radius: 3px; "
               f"padding: 1px 4px; font-family: monospace; }}")
        for i, browser in enumerate(self._browsers):
            browser.document().setDefaultStyleSheet(css)
            browser.setHtml(self._strip_inline_bg(_SECTIONS[i][1]))

    @staticmethod
    def _strip_inline_bg(html: str) -> str:
        return html.replace(' style="background:#f0f4f8;"', '')

    def show_section(self, title: str):
        for i, (t, _) in enumerate(_SECTIONS):
            if t == title:
                self._tabs.setCurrentIndex(i)
                break
