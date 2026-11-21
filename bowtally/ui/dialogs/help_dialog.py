# -*- coding: utf-8 -*-
"""App-Hilfe Dialog: Inhaltsverzeichnis + HTML-Ansicht."""
import re

from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (QDialog, QFrame, QHBoxLayout, QLineEdit, QListWidget,
                                QListWidgetItem, QStackedWidget, QTextBrowser,
                                QVBoxLayout, QWidget)

from bowtally.ui import button, restore_geom, save_geom, theme
from bowtally.ui.components.search_bar import PLACEHOLDER as SEARCH_PLACEHOLDER

_SECTIONS = [
    ("Übersicht", """
<h2>BowTally – Übersicht</h2>
<p>BowTally ist eine Turnierverwaltungs-App für 3D-Bogensport-Vereine. Die wichtigsten Module:</p>
<ul>
  <li><b>Dashboard</b> – Überblick über Turniere und Stammdaten</li>
  <li><b>Turniere</b> – anlegen, bearbeiten, phasenweise durchführen</li>
  <li><b>Kalender</b> – alle Turniere im Jahres-, Monats-, Wochen- und Tagesraster</li>
  <li><b>Schützen</b> und <b>Mitglieder</b> – Stammdaten; Helfer plant man im Turnier (Tab <b>Helfer</b>)</li>
  <li><b>Regelwerke &amp; Klassen</b> – Punktverteilung und Wertungsgruppen</li>
  <li><b>Inventar</b> – alle Ausrüstungsgegenstände des Vereins (Ziele, Tische, Pavillons …)</li>
  <li><b>Logbuch</b> – Protokoll der Aktivitäten</li>
  <li><b>Einstellungen</b> – Vereinsprofil, E-Mail-Vorlagen, Druck, Backup, Updates und Design</li>
</ul>
<h3>Navigation</h3>
<p>Links in der Seitenleiste wechselst du zwischen den Modulen. Ein Klick auf das Logo
oben führt zurück zum Dashboard. Unten findest du <b>Einstellungen</b>, <b>Hilfe</b> und
<b>Über BowTally</b>. Reihenfolge und Sichtbarkeit der Einträge stellst du unter
Einstellungen → System → Allgemein → Navigation ein.</p>
<p>Ein orangefarbener Punkt an <b>Turniere</b> weist darauf hin, dass beim aktiven Turnier die
maximale Teilnehmerzahl erreicht ist oder dass ein Turnier in der Phase „Schießen“ läuft.</p>
<h3>Dialoge</h3>
<p>In Bearbeiten-Dialogen ist <b>Speichern</b> blau und wird rot, sobald du etwas geändert hast;
<b>Abbrechen</b> ist schwarz.</p>
<p>Hinweise und Bestätigungen (z. B. „Gespeichert“) erscheinen als kleine <b>Infofenster
oben rechts</b> im jeweiligen Fenster und verschwinden nach einigen Sekunden von selbst; ein
Klick schließt sie sofort. Neue Meldungen stehen oben, ältere rücken nach unten.</p>
<h3>Aktives Turnier</h3>
<p>Wenn du ein Turnier öffnest, erscheint im oberen Teil der Seitenleiste ein Turnier-Block mit
Name, Phase und diesen Schnellzugriffen:</p>
<ul>
  <li><b>Wechseln</b> – anderes Turnier öffnen; das <b>✕</b> schließt das Turnier wieder</li>
  <li><b>Turnier-Dashboard</b> – Kennzahlen des Turniers</li>
  <li><b>Turnier-Details</b> – Tabs wie Teilnehmer, Parcours oder Ergebnisse</li>
  <li><b>Leitfaden</b> – Aufgaben der aktuellen Phase</li>
  <li><b>Nächste Phase</b> – Phasenwechsel (siehe „Turnierphasen &amp; Leitfaden“)</li>
  <li><b>Phasenwechsel-Protokoll</b> – alle bisherigen Phasenwechsel</li>
</ul>
<p>Der Eintrag <b>Turniere</b> ist ausgeblendet, solange ein Turnier geöffnet ist; die Liste
erreichst du dann über <b>Alle Turniere</b> in den Turnier-Details. Nach dem Öffnen eines Turniers
zeigt BowTally zuerst den Leitfaden. Beim nächsten Start wird das zuletzt aktive Turnier
wieder geöffnet.</p>
<h3>Statusleiste</h3>
<p>Ganz unten stehen der Pfad der Datenbank und die Programmversion. Das Fragezeichen öffnet
diese Hilfe (<code>F1</code>).</p>
"""),
    ("Turniere", """
<h2>Turniere</h2>
<h3>Turnierliste</h3>
<p>Die Liste zeigt Datum, Name, Ort, Phase, Teilnehmerzahl und Regelwerk. Abgeschlossene Turniere
sind ausgeblendet, bis du <i>Abgeschlossene Turniere anzeigen</i> aktivierst. Die Suche findet
Name, Ort oder Phase.</p>
<h3>Turnier anlegen</h3>
<p>Über <b>Neues Turnier</b> (Strg+N) öffnet sich der Turnier-Assistent. Er führt durch
acht Schritte: Grunddaten, Konfiguration, Bogenklassen, Fristen und Zeiten, Startgebühren,
Kontakt und Bankdaten, Hinweise und Texte sowie Zusammenfassung. Details stehen im
Abschnitt „Turnier-Assistent“.</p>
<h3>Turnierphasen</h3>
<ol>
  <li><b>Entwurf</b> – Turnierdaten werden angelegt und können frei bearbeitet werden</li>
  <li><b>Ausschreibung</b> – Kontakt, Bank und Startgebühren festlegen, Ausschreibungs-PDF erstellen</li>
  <li><b>Vorbereitung</b> – Parcours und Helfer planen</li>
  <li><b>Anmeldung</b> – Anmeldungen erfassen, bestätigen und Zahlungen verbuchen</li>
  <li><b>Einschreibung</b> – Turniertag: Check-in vor Ort</li>
  <li><b>Schießen</b> – Ergebniseingabe</li>
  <li><b>Auswertung</b> – Ergebnisse prüfen, Ergebnisliste erstellen, Siegerehrung vorbereiten</li>
  <li><b>Abgeschlossen</b> – Turnier beendet, Daten gesperrt</li>
</ol>
<p>Mit <b>Nächste Phase</b> in der Seitenleiste (oder im Leitfaden) wechselst du in die nächste
Phase. BowTally prüft dabei Voraussetzungen, siehe „Turnierphasen &amp; Leitfaden“.</p>
<h3>Warteliste</h3>
<p>Ist <i>Warteliste bei Vollbelegung</i> (Einstellungen → Turnierverwaltung → Allgemein) auf
<b>Automatisch (Warteliste)</b> eingestellt, werden überzählige Anmeldungen automatisch auf die
Warteliste gesetzt (Status „Auf Warteliste“). Bei <b>Gesperrt (kein Nachrücken)</b> lassen sich bei
voller Teilnehmerzahl keine weiteren Schützen zuweisen.</p>
<p>Wird ein Teilnehmer zurückgezogen, disqualifiziert oder entfernt, rücken Wartelistenplätze
in der Reihenfolge der Anmeldung nach (Status wird „Gemeldet“). Schützen desselben Vereins rücken
nur gemeinsam nach, wenn für alle Platz ist. Über <b>Benachrichtigen</b> in der Meldung
kannst du die Nachrücker per E-Mail informieren.</p>
<h3>Turnier kopieren</h3>
<p>Ein Turnier kann als Vorlage kopiert werden (ohne Teilnehmer und Ergebnisse). Parcours-Ziele und
Preise werden mit übernommen. Nützlich für wiederkehrende Turniere.</p>
<h3>Turnier löschen</h3>
<p><b>Löschen</b> entfernt das Turnier nach Rückfrage endgültig – mit allen Teilnehmern und
erfassten Ergebnissen.</p>
"""),
    ("Turnierphasen & Leitfaden", """
<h2>Turnierphasen &amp; Leitfaden</h2>
<h3>Was ist in welcher Phase möglich?</h3>
<p>Die Tabs im Turnier (Turnier-Details) hängen von der Phase ab.
<b>Teilnehmer</b>, <b>Preise</b>, <b>Helfer</b> und <b>Notizen</b> sind immer sichtbar.</p>
<table border="0" cellspacing="0" cellpadding="5" style="border-collapse:collapse;">
  <tr><td><b>Entwurf</b></td><td>Startgebühren; „Turnierdaten bearbeiten“ möglich</td></tr>
  <tr><td><b>Ausschreibung</b></td><td>Startgebühren; „Turnierdaten bearbeiten“ möglich; Ausschreibungs-PDF erstellen</td></tr>
  <tr><td><b>Vorbereitung</b></td><td>neu: <i>Parcours</i> und <i>Zeitplan</i>; Startgebühren und „Turnierdaten bearbeiten“ nicht mehr verfügbar</td></tr>
  <tr><td><b>Anmeldung</b></td><td>Anmeldungen bestätigen, Zahlungen verbuchen</td></tr>
  <tr><td><b>Einschreibung</b></td><td>neu: <i>Einschreibung</i> (Check-in)</td></tr>
  <tr><td><b>Schießen</b></td><td>neu: <i>Ergebniseingabe</i>; Teilnehmer lassen sich nicht mehr zuweisen oder entfernen</td></tr>
  <tr><td><b>Auswertung</b></td><td>neu: <i>Auswertung</i> (Rangliste, Ergebnisliste); der Check-in-Tab entfällt</td></tr>
  <tr><td><b>Abgeschlossen</b></td><td>alles nur noch lesbar; Export möglich</td></tr>
</table>
<p>Der Tab <i>Zeitplan</i> erscheint nur, wenn im Assistenten keine
Auslosung eingestellt ist.</p>
<h3>Turnierdaten bearbeiten</h3>
<p>Der Button <b>Turnierdaten bearbeiten</b> in den Turnier-Details öffnet
den Assistenten und ist nur in den Phasen <i>Entwurf</i> und
<i>Ausschreibung</i> sichtbar. In der Turnierliste ist
<b>Bearbeiten</b> bis einschließlich <i>Anmeldung</i> möglich und ab der
Einschreibung gesperrt.</p>
<h3>Phasenwechsel und Voraussetzungen</h3>
<p>Vor jedem Wechsel zeigt BowTally an, was fehlt. <b>Rot</b> (muss erfüllt
sein) blockiert den Wechsel, <b>Gelb</b> (Hinweis) lässt ihn nach Rückfrage
zu. Hinweise und offene manuelle Leitfaden-Aufgaben werden im Protokoll
festgehalten.</p>
<table border="0" cellspacing="0" cellpadding="5" style="border-collapse:collapse;">
  <tr><td><b>→ Vorbereitung</b></td><td>muss: Regelwerk, Bogenklassen, Turnierdatum nicht in der Vergangenheit · Hinweis: Kontakt, Bankverbindung, Ausschreibung erstellt</td></tr>
  <tr><td><b>→ Anmeldung</b></td><td>muss: Startgebühren, Anmeldefrist · Hinweis: Ausschreibung aktuell, maximale Teilnehmerzahl</td></tr>
  <tr><td><b>→ Einschreibung</b></td><td>muss: mindestens ein bestätigter Teilnehmer · Hinweis: alle bestätigt, alle bezahlt, Anmeldefrist abgelaufen</td></tr>
  <tr><td><b>→ Schießen</b></td><td>muss: mindestens ein Teilnehmer eingecheckt · Hinweis: alle erwarteten eingecheckt, alle bezahlt</td></tr>
  <tr><td><b>→ Auswertung</b></td><td>muss: Ergebnisse vorhanden · Hinweis: Ergebnisse vollständig</td></tr>
  <tr><td><b>→ Abgeschlossen</b></td><td>Hinweis: Ergebnisliste erstellt, alle bezahlt · danach sind keine Änderungen mehr möglich</td></tr>
</table>
<h3>Phase zurücksetzen und Protokoll</h3>
<p><b>Phasenwechsel-Protokoll</b> (Seitenleiste) listet Zeitpunkt, Von, Nach,
Erzwungen und Warnungen aller Wechsel. Dort führt <b>← Zur vorherigen Phase</b>
nach Rückfrage einen Schritt zurück; der Schritt wird als erzwungener Wechsel
protokolliert. Die Phasenliste in der Seitenleiste zeigt, wann welche Phase
erreicht wurde.</p>
<h3>Leitfaden</h3>
<p>Der <b>Leitfaden</b> zeigt für die aktuelle Phase: eine Beschreibung, die
<b>Aufgaben</b>, die <b>Voraussetzungen</b> für die nächste Phase (Ampel) und –
je nach Phase – einen Status und Kennzahlen (Anmeldungen, Einschreibung,
Ergebnisfortschritt, ausstehende Zahlungen). Aufgaben mit Button springen
direkt in die passende Ansicht (z. B. <i>Bankdaten eingeben</i>, <i>PDF
generieren</i>, <i>Auslosung starten</i>, <i>Unvollständige anzeigen</i>). Manche
Aufgaben hakst du von Hand ab (z. B. „Parcours planen und aufbauen“,
„Helfer einteilen“); andere erledigen sich automatisch, sobald die Daten
vollständig sind. In der Phase <i>Abgeschlossen</i> bietet der Leitfaden
<b>Alle Turnierdaten exportieren</b>, die Nachbesprechung und die Notizen
(siehe „Notizen &amp; Nachbesprechung“).</p>
<p>Das <b>Turnier-Dashboard</b> zeigt dieselbe „Nächste Aufgabe“ und weitere
Kennzahlen, siehe „Dashboard &amp; Logbuch“.</p>
"""),
    ("Turnier-Assistent", """
<h2>Turnier-Assistent</h2>
<p>Der Assistent legt Turniere an, kopiert sie oder bearbeitet sie. Oben zeigt
eine Fortschrittsleiste den aktuellen Schritt; die Zusammenfassung enthält
<b>Bearbeiten</b>-Links, die zum jeweiligen Schritt zurückspringen.</p>
<h3>1 Grunddaten</h3>
<p>Turniername (Pflicht), Datum, Ort, Veranstalter und eine interne
Beschreibung. Der Button <b>Vereinsdaten übernehmen</b> in der Fußzeile trägt
Veranstalter und Ort aus dem Vereinsprofil ein; bereits geänderte Felder
werden erst nach Rückfrage überschrieben. Der Button erscheint nur, wenn im
Vereinsprofil Name oder Ort hinterlegt sind.</p>
<h3>2 Konfiguration</h3>
<p><b>Wertungsmodus</b>: <i>Zielwertung</i> (Punkte je Ziel und Schuss),
<i>Rundenwertung</i> (Punkte je Runde) oder <i>Gesamtwertung</i> (nur Gesamtpunkte).</p>
<p><b>Maximale Teilnehmerzahl</b> (<code>0</code> = keine Begrenzung); darunter zeigt die
<b>Auslastung</b>, wie viele Plätze bereits belegt sind.</p>
<a name="startgruppen"></a><p><b>Auslosung oder Startgruppen:</b> Mit <i>Teilnehmer per Auslosung
einteilen</i> werden die Gruppen später per Auslosung vergeben (das Feld
Startgruppen ist dann ausgeblendet und der Tab <i>Zeitplan</i> entfällt). Ohne
Auslosung füllt BowTally <b>Startgruppen</b> automatisch: maximale Teilnehmerzahl
geteilt durch <i>Teilnehmer pro Gruppe</i> (Einstellungen → Turnierverwaltung →
Allgemein), aufgerundet – z. B. 120 Teilnehmer bei 5 pro Gruppe ergibt die Gruppen
1 bis 24. Ohne Begrenzung sind die Gruppen 1 bis 10 vorbelegt. Das Feld bleibt
änderbar (z. B. <code>A, B, C, D</code>); eine eigene Eingabe wird nicht mehr
automatisch überschrieben, bestehende Turniere behalten ihre Gruppen. Neue Teilnehmer
werden reihum auf die Gruppen verteilt und im Tab <i>Zeitplan</i> bekommen die
Gruppen Startzeiten.</p>
<p><b>Rundenkonfiguration:</b> Jede Runde hat Bezeichnung, Regelwerk (oder
„Turnier-Standard“), Ziele, Pfeile und Entfernung (Standard, bekannt,
unbekannt). Mit <b>+ Runde</b> fügst du Runden hinzu, der Papierkorb entfernt
sie (mindestens eine bleibt). Die erste Runde bestimmt Regelwerk,
Scheibenzahl und Pfeile des Turniers. Bei neuen Turnieren ist das als
Standard markierte Regelwerk (★ in der Regelwerke-Liste) vorgewählt. Ist im
Vereinsprofil eine Parcours-Beschreibung hinterlegt, wird sie automatisch in
„Hinweise zum Parcours“ übernommen, solange das Turnier dort noch nichts stehen hat.</p>
<h3>3 Bogenklassen</h3>
<p>Klassen per Klick an- und abwählen. Zuerst stehen die Standard-Klassen, danach die
eigenen, jeweils alphabetisch zeilenweise von links nach rechts. Mit
<b>Nur eigene Klassen anzeigen</b> (standardmäßig angehakt, sobald es eigene Klassen gibt)
werden die Standard-Klassen ausgeblendet; eine bereits gewählte ausgeblendete Klasse bleibt
gewählt, ein Hinweis rechts nennt ihre Anzahl. <b>Alle</b> und <b>Keine</b> wirken auf die
angezeigten Klassen, <b>Eigene</b> wählt nur die benutzerdefinierten. Mindestens eine Klasse
ist nötig.</p>
<h3>4 Fristen und Zeiten</h3>
<p>Anmeldefrist, Einschreibung ab und Schießbeginn. Bei <b>Einschießen erlaubt</b> erscheint
das Feld <b>Einschießbereich</b>; es ist dann Pflicht, sonst kommst du nicht
weiter. Der Bereich erscheint in der Ausschreibung.</p>
<h3>5 Startgebühren</h3>
<p>Neue Turniere starten mit den Gebührenvorlagen; Bezeichnung und Betrag sind
direkt änderbar, mit <b>Zeile hinzufügen</b> kommen weitere dazu. Ohne Gebühr
ist kein Wechsel in die Anmeldephase möglich (die Zusammenfassung warnt
darauf).</p>
<h3>6 Kontakt und Bankdaten</h3>
<p>Kontaktperson (Auswahl aus den Rollen des Vereinsvorstands, vorbelegt mit
der Standard-Kontaktperson), Telefon, E-Mail, Kontoinhaber, IBAN, BIC und
Verwendungszweck mit den Platzhaltern <code>{name}</code> und
<code>{bow_class}</code>. <b>Vereinsdaten übernehmen</b> füllt diese Felder aus
Vereinsprofil, Vorstand und Bankdaten.</p>
<h3>7 Hinweise und Texte</h3>
<p>Einleitungstext, Hinweise zum Parcours, wichtige Hinweise (eine Zeile je
Hinweis; vorbelegt aus Einstellungen → Turnierverwaltung → Textvorlagen) und Abschlusstext.
Sie erscheinen in der Ausschreibung.</p>
<h3>8 Zusammenfassung</h3>
<p>Prüfe die Angaben und speichere mit <b>Turnier erstellen</b> bzw.
<b>Speichern</b>. Die Checkbox <b>Ausschreibung jetzt generieren</b> in der
Fußzeile erstellt direkt das Ausschreibungs-PDF; sie ist bei neuen Turnieren
vorgekreuzt, beim Bearbeiten nicht. Über diesen Weg wird nur das PDF erstellt
– das Angebot für die Ankündigungs-Mail erscheint beim Erstellen aus dem
Leitfaden (siehe „E-Mail-Funktionen“).</p>
<h3>Ausschreibungs-PDF</h3>
<p>Das PDF enthält Vereinskopf mit Logo, Einladung, Termin und Ablauf, Parcours,
Bogenklassen, Startgeld, Anmeldung und Überweisung, Kontakt, Hinweise und
Abschlusstext. Ist unter Regelwerke → Turnierregeln der Text
<i>Teilnahmebedingungen</i> gepflegt, folgt er als eigene Seite am Ende.
Wurden Turnierdaten nach dem Erstellen geändert, markieren Leitfaden und
Dashboard die Ausschreibung als veraltet; dort kannst du sie neu
generieren.</p>
"""),
    ("Schützen & Teilnehmer", """
<h2>Schützen &amp; Teilnehmer</h2>
<h3>Schützen-Stammdaten</h3>
<p>Im Modul <b>Schützen</b> verwaltest du die Stammdaten aller Vereinsmitglieder.
Über <b>Importieren</b> lassen sich Schützenlisten als CSV oder Excel einlesen –
BowTally erkennt gängige Spaltenbezeichnungen automatisch. Zu jedem Schützen
gehört eine optionale <b>Passnummer</b>. Beim Import gilt ein Schütze als bereits
vorhanden, wenn Passnummer <i>und</i> Name übereinstimmen – oder, ohne Passnummer,
der Name (bei bekanntem Geburtsdatum auch dieses).</p>
<p>Datums-, Uhrzeit- und Betragsfelder sind vorformatiert (<code>__.__.____</code>,
<code>__:__</code>, <code>__,__ €</code>): Einfach ins Feld klicken und die Ziffern
tippen. Bei Beträgen wächst die Maske mit, wenn du mehr als zwei Stellen vor dem Komma
tippst (bis <code>____,__ €</code>); ein Komma oder Punkt springt zu den Cent. Den Kalender öffnet das Symbol
rechts im Datumsfeld oder F4.</p>
<p>Schützen können als <b>inaktiv</b> markiert werden und werden dann aus
Auswahllisten ausgeblendet. Die Checkbox <i>Inaktive Schützen anzeigen</i>
blendet sie wieder ein. Schützen mit Turnierteilnahme lassen sich nicht löschen;
BowTally bietet stattdessen an, sie zu deaktivieren.</p>
<p>Der Bearbeiten-Dialog zeigt im Tab <b>Turnierhistorie</b> alle bisherigen
Teilnahmen mit Rang und Punkten. Die Tabs <b>Notizen</b> (das Feld nimmt die halbe Höhe ein) und
<b>Dokumente</b> (z.&nbsp;B. Ausweis oder Startberechtigung) sind eigene Tabs; Dokumente werden in
den Datenordner kopiert, sind im Backup enthalten und lassen sich erst nach dem ersten Speichern
hinzufügen. Zwei Checkboxen gibt es nur mit hinterlegter
E-Mail-Adresse (ohne Adresse sind sie ausgegraut und abgewählt):</p>
<ul>
  <li><b>Bei neuen Turnieren per E-Mail benachrichtigen</b> – der Schütze erhält
      die Ankündigungs-Mail mit der Ausschreibung (nur wenn er aktiv ist)</li>
  <li><b>Ergebnisversand per E-Mail</b> – der Schütze ist beim Ergebnisversand
      vorausgewählt</li>
</ul>
<h3>E-Mail-Benachrichtigungen</h3>
<p>Im Schützen-Dialog gibt es zwei Checkboxen, die nur mit hinterlegter
E-Mail-Adresse aktivierbar sind (ohne Adresse sind sie ausgegraut und
abgewählt):</p>
<ul>
  <li><b>Bei neuen Turnieren per E-Mail benachrichtigen</b> – der Schütze
      erhält die Ankündigungs-Mail mit der Ausschreibung (nur wenn er aktiv ist)</li>
  <li><b>Ergebnisversand per E-Mail</b> – der Schütze ist beim
      Ergebnisversand vorausgewählt</li>
</ul>
<h3>Teilnehmer-Anmeldung</h3>
<p>Im Turnier unter <b>Teilnehmer</b> weist du Schützen über
<b>Schütze zuweisen</b> dem Turnier zu. Bei mehreren Schützen kannst du die
Bogenklassen im folgenden Dialog individuell anpassen. <b>Neuer Schütze</b>
(links daneben) legt einen Schützen in den Stammdaten an und weist ihn
gleichzeitig dem geöffneten Turnier zu.</p>
<p>Jede Person kann nur einmal am Turnier teilnehmen. BowTally prüft das beim
Zuweisen, beim Import, bei Walk-ins und bei <b>Neuer Schütze</b> über den
Schützen-Datensatz und zusätzlich über den Namen (Groß-/Kleinschreibung egal; zwei
Personen mit gleichem Namen werden nur durch unterschiedliche Geburtsdaten
unterschieden). Doppelte werden übersprungen und gemeldet; bei <b>Neuer Schütze</b>
kannst du den gerade angelegten doppelten Stammdatensatz direkt wieder löschen.</p>
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
    ("Check-in & Startgebühren", """
<h2>Check-in &amp; Startgebühren</h2>
<h3>Startgebühren anlegen</h3>
<p>Der Tab <b>Startgebühren</b> ist nur in den Phasen <i>Entwurf</i> und
<i>Ausschreibung</i> sichtbar und bearbeitbar. Er enthält Bezeichnung, Betrag
und Beschreibung je Gebühr (<b>Neue Gebühr</b>, Strg+N). <b>Vorlagen laden</b>
kopiert die Standard-Gebühren hinzu. Eine Gebühr, die Teilnehmern zugewiesen
ist, lässt sich nicht löschen. Die Gebühren erscheinen in der Ausschreibung
und in der Einnahmenübersicht.</p>
<h3>Gebühren zuweisen und Zahlungen verbuchen</h3>
<p>Zugewiesen und verbucht wird im Tab <b>Teilnehmer</b>: per Doppelklick auf
die Gebühr, über <b>Gebühr zuweisen …</b> im Kontextmenü oder beim Bestätigen
einer Anmeldung. Der Zahlungsstatus lautet <b>Ausstehend</b>,
<b>Erwartet</b> oder <b>Bezahlt</b>. <b>Zahlung eingegangen</b> setzt „Bezahlt“
mit dem heutigen Datum; <b>Zahlung als ausstehend markieren</b> macht es
rückgängig.</p>
<h3>Check-in am Turniertag</h3>
<p>Der Tab <b>Einschreibung</b> ist in den Phasen <i>Einschreibung</i> und
<i>Schießen</i> aktiv. Gib Name oder Startnummer ein und drücke <b>Enter</b> –
der Teilnehmer wird eingecheckt. Der Button wechselt zu <b>Auschecken</b>,
wenn der Teilnehmer bereits eingecheckt ist (Status danach „Bestätigt“). Oben
stehen <i>Eingecheckt / Erwartet</i> und die Auslastung, rechts in derselben Zeile
Suchfeld, <b>Einchecken</b> und <b>Als Walk-in erfassen</b>. Ist die Startgebühr
nicht als eingegangen markiert, erscheint die Warnung „Startgebühr nicht als
eingegangen markiert“.</p>
<h3>Walk-in</h3>
<p><b>Als Walk-in erfassen</b> (Strg+N) legt einen Teilnehmer vor Ort an und
checkt ihn direkt ein: Vorname und Nachname sind Pflicht, dazu Verein,
Bogenklasse, Startgebühr und die Checkbox <i>Startgebühr bar bezahlt</i>.
Bei voller Teilnehmerzahl ist der Button gesperrt.</p>
<h3>Einschreibeliste</h3>
<p>Die <b>Einschreibeliste</b> druckst du als PDF über die Aufgabe
„Teilnehmerliste drucken“ im Leitfaden der Phase <i>Einschreibung</i>.</p>
"""),
    ("Parcours, Zeitplan & Preise", """
<h2>Parcours, Zeitplan &amp; Preise</h2>
<h3>Parcours-Planung</h3>
<p>Der Tab <b>Parcours</b> (ab Phase <i>Vorbereitung</i>) enthält alle Ziele (Scheiben
bzw. 3D-Tiere). Mit <b>Neues Ziel</b> legst du eins an. Felder: Ziel-Nr., Tier / Bezeichnung, Distanz (m),
Pfeilstoppklasse, Geländetyp, Max. Gruppengröße und Helfernotiz.</p>
<p>Über <b>Aus Inventar …</b> im Bearbeitungsdialog lassen sich Bezeichnungen
direkt aus dem Vereinsinventar übernehmen (nur Artikel mit <i>Für Parcoursplanung
verwenden</i>). Die Reihenfolge ist per <b>Drag-and-Drop</b> änderbar und wird
dauerhaft gespeichert.</p>
<p>Zusätzlich wählst du Inventarartikel mit einer <b>angeforderten Menge</b> aus. Der
Parcoursplan zeigt, ob der Bestand reicht oder wie viele Einheiten fehlen. Für dieses
Turnier gemietetes oder gekauftes Material legst du als <b>Einmalposten</b> an; er gehört
nicht zum Inventar und zählt nicht zum Inventarwert.</p>
<p>Drucken: <b>Aufbauplan</b> (mit Helfernotizen für Helfer) und
<b>Zielplan</b> (ohne Notizen für Teilnehmer) als PDF.</p>
<h3>Zeitplan</h3>
<p>Der Tab <b>Zeitplan</b> erscheint ab Phase <i>Vorbereitung</i>, sofern im
Assistenten keine Auslosung eingestellt ist. Hier werden Startgruppen und
-zeiten verwaltet.</p>
<a name="auslosung"></a><h3>Auslosung</h3>
<p>Wird im Turnier-Assistenten unter <i>Konfiguration</i> <b>Teilnehmer per
Auslosung einteilen</b> aktiviert, ersetzt die Auslosung den Zeitplan. Der
Button <b>Auslosung …</b> im Teilnehmer-Tab verteilt Teilnehmer zufällig auf
Gruppen. Die maximalen Gruppengrößen aus dem Parcours werden dabei
berücksichtigt.</p>
<h3>Preise</h3>
<p>Der Tab <b>Preise</b> ist immer sichtbar und enthält die Preisgestaltung des
Turniers.</p>
<h3>Wertungszettel</h3>
<p>Im Auslosungs-Dialog wählst du eine <b>Wertungszettel-Vorlage</b>. Nach der Auslosung
erstellt BowTally dann für jeden Teilnehmer einen Wertungszettel als PDF; „Keinen“ führt nur
die Auslosung durch. Weitere Listen: <b>Starterfeld drucken</b> (⋮-Menü der Teilnehmer, nach
Startgruppe sortiert) und <b>Helferliste drucken</b> (Tab Helfer).</p>
"""),
    ("Ergebnisse & Wertung", """
<h2>Ergebnisse &amp; Wertung</h2>
<h3>Ergebniseingabe</h3>
<p>Der Tab <b>Ergebniseingabe</b> erscheint ab der Phase <i>Schießen</i>. Je Teilnehmer gibt es
eine Zeile, je Scheibe (bei mehreren Pfeilen je Schuss) eine Spalte. Tippe eine Punktzahl oder wähle
eine Zone aus der liste. Navigiere mit <b>Tab / Umschalt+Tab</b> zwischen Scheiben und
mit <b>Enter / ↓ / ↑</b> zwischen Teilnehmern; <b>Esc</b> verwirft die laufende Eingabe.
Jede Zelle wird sofort gespeichert; <b>Speichern</b> (Strg+S) bestätigt dies nur.</p>
<h3>Filter und Hilfen</h3>
<ul>
  <li><b>Klassen-Tabs</b>, Gruppenfilter (nur sichtbar, wenn Startgruppen existieren) und Suche
      nach Name oder Startnummer</li>
  <li><b>Nur unvollständige</b> zeigt nur Teilnehmer mit fehlenden Ergebnissen. Dieser Filter, die
      Suche, das Gruppen-Dropdown, die Klassen-Tabs und <b>Speichern</b> stehen bei allen
      Wertungsarten zur Verfügung</li>
  <li>Rechtsklick auf eine Spaltenüberschrift setzt die Scheibe für alle sichtbaren
      Teilnehmer auf eine Zone (mit Rückfrage)</li>
  <li>Bei mehreren Runden wählst du die Runde über Tabs über der Tabelle</li>
  <li>Zählt das Regelwerk Kills oder X-Treffer, erscheinen zusätzliche Spalten</li>
</ul>
<p>Bei den Wertungsmodi <i>Rundenwertung</i> und <i>Gesamtwertung</i> trägst du stattdessen
die Punkte je Runde bzw. die Gesamtpunkte in einer einfachen Tabelle ein. Dort
werden nur Zahlen angenommen.</p>
<p>Ist die Auswertung geschlossen (Ergebnisliste erstellt) oder das Turnier abgeschlossen, ist
die Eingabe gesperrt.</p>
<h3>Rang berechnen</h3>
<p>Der Rang wird beim Öffnen der Auswertung neu berechnet, wenn <i>automatisch neu berechnen</i>
aktiv ist (Einstellungen → Turnierverwaltung → Allgemein). Andernfalls klickst du auf
<b>Neu berechnen</b> (F5). Bei Punktgleichstand gelten die Gleichstandsregeln des Regelwerks; bleiben
Teilnehmer gleichauf, steht „ex aequo“ beim Rang.</p>
<a name="gleichstand"></a><h3>Gleichstand</h3>
<p>Die Regeln für einen Punktgleichstand stellst du im jeweiligen Regelwerk ein
(<b>Regelwerke</b> → Regelwerk bearbeiten). Reihenfolge:</p>
<ol>
  <li><b>Kills</b> (nur 3D-Parcours) – wenn „Kills zählen“ und „Bei gleicher Punktzahl gewinnt
      die höhere Anzahl an Kills“ eingeschaltet sind</li>
  <li><b>X-Treffer</b> (nur Scheibe) – ebenso</li>
  <li><b>Treffer in der höchsten Wertung</b> – wenn eingeschaltet, zählt die Anzahl der Treffer ab
      der höchsten Zone. Mit <i>Diese Treffer vor Kills und X-Treffern prüfen</i> rückt dieser
      Schritt an die erste Stelle (so z.&nbsp;B. bei der DBSV-Außenrunde: erst 10er, dann X;
      die WA-Außenrunde prüft erst X, dann 10er)</li>
</ol>
<p>Bleibt es danach gleich, teilen sich die Teilnehmer den Rang (zwei erste Plätze). Verlangt das
Regelwerk bei Gleichstand ein <b>Stechen</b> (z.&nbsp;B. IBO, IFAA), schaltest du
<i>Stechen erforderlich</i> ein: Ergebnisansicht, Ergebnisliste (PDF) und der Wechsel nach
„Abgeschlossen“ weisen dann auf Gleichstände auf Platz 1–3 hin. Das Ergebnis des Stechens trägst
du in der <b>Auswertung</b> über <b>Stechen eintragen</b> ein (Punkte je Teilnehmer, wer mehr hat,
steht vorn; gleiche Werte bleiben gleichauf, z.&nbsp;B. wenn das Stechen weitergeht). Das geht,
bis die Ergebnisliste erstellt ist. Eingetragene Werte erscheinen als Spalte <b>Stechen</b> in der
Ergebnisansicht, in den Exporten und in der Ergebnisliste.
Bei <b>Zielwertung</b> werden Kills und X-Treffer aus den gewählten Zonen gezählt, bei
<b>Gesamtwertung</b> und <b>Rundenwertung</b> trägst du die Anzahl in der Spalte neben den
Punkten ein (erst die Punkte, dann die Anzahl).</p>
<h3>Exportieren</h3>
<p>Ranglisten lassen sich als Excel, OpenDocument oder CSV sowie als PDF exportieren, siehe
„Auswertung &amp; Ergebnisliste“. Einschreibe- und Teilnehmerlisten exportierst du über die
jeweiligen Ansichten (siehe „Import &amp; Export“).</p>
"""),
    ("Auswertung & Ergebnisliste", """
<h2>Auswertung &amp; Ergebnisliste</h2>
<h3>Ergebnisliste erstellen</h3>
<p><b>Ergebnisliste erstellen</b> erzeugt das druckfertige PDF. Beim ersten Mal
fragt BowTally: „Die Auswertung wird nun geschlossen. Dieser Schritt kann
nicht rückgängig gemacht werden.“ Nach der Bestätigung ist die
<b>Ergebniseingabe unwiderruflich schreibgeschützt</b>, ebenso die Helfer des
Turniers. Danach kannst du die
Ergebnisliste beliebig oft neu erstellen.</p>
<h3>Aktionen nach dem Erstellen</h3>
<p>Diese Buttons sind erst aktiv, nachdem die Ergebnisliste erstellt wurde
(vorher steht im Tooltip „Bitte zuerst die Ergebnisliste erstellen“):</p>
<ul>
  <li><b>Urkunden drucken</b> – Urkunden für die Podiumsplätze als PDF</li>
  <li><b>Preis- und Siegerliste</b> – Rangliste je Bogenklasse mit den
      zugewiesenen Preisen als PDF</li>
  <li><b>Exportieren</b> – Excel, OpenDocument, CSV oder <b>PDF (.pdf)</b>
      (Dateiname frei wählbar)</li>
  <li><b>Ergebnisse per E-Mail senden</b> – Ergebnisse per E-Mail an die Teilnehmer,
      siehe „E-Mail-Funktionen“</li>
</ul>
<h3>Voraussetzungen und Abschluss</h3>
<p>Im Leitfaden der Phase <i>Auswertung</i> prüfst du die Vollständigkeit
(<b>Unvollständige anzeigen</b>), erstellst die Ergebnisliste, bereitest die
Siegerehrung vor und hängst die Liste aus oder versendest sie. Beim Wechsel zu
<i>Abgeschlossen</i> weist BowTally darauf hin, falls die Ergebnisliste noch
nicht erstellt wurde oder Zahlungen offen sind.</p>
<h3>Speichern</h3>
<p>Die Ergebnisseingabe speichert jede Zelle sofort. Mit <b>Speichern</b>
(Strg+S) bestätigst du den aktuellen Stand.</p>
"""),
    ("Notizen & Nachbesprechung", """
<h2>Notizen &amp; Nachbesprechung</h2>
<h3>Notizen-Tab</h3>
<p>Der Tab <b>Notizen</b> im Turnier ist in jeder Phase sichtbar und enthält ein
freies Textfeld für interne Notizen zum Turnier. Mit <b>Notizen speichern</b>
sicherst du den Text. Die Notizen erscheinen <b>nicht</b> in der Ausschreibung.
In der Phase <i>Abgeschlossen</i> sind sie schreibgeschützt.</p>
<p>Die Notizen sind außerdem sichtbar:</p>
<ul>
  <li>im Turnier-Dashboard in der Karte „Aktuelle Phase“</li>
  <li>im Leitfaden der Phase <i>Abgeschlossen</i></li>
  <li>im Export „Alle Turnierdaten exportieren“ (Blatt <i>Notizen</i>)</li>
</ul>
<h3>Nachbesprechung</h3>
<p>Im Leitfaden der Phase <i>Abgeschlossen</i> hältst du in der
<b>Nachbesprechung</b> fest, was gut lief und was beim nächsten Turnier besser
werden soll. <b>Notizen speichern</b> sichert den Text; er wird ebenfalls mit
„Alle Turnierdaten exportieren“ ausgegeben. Dort stehen auch eine
Zusammenfassung mit Datum, Teilnehmerzahl und Einnahmen.</p>
"""),
    ("Inventar & Kalender", """
<h2>Inventar &amp; Kalender</h2>
<h3>Vereinsinventar</h3>
<p>Das Modul <b>Inventar</b> (Seitenleiste) verwaltet alle wiederverwendbaren Gegenstände
für Turniere. Die Liste lässt sich oben links nach <b>Kategorie</b> filtern. Jeder Artikel hat
einen Dialog mit den Tabs <b>Stammdaten</b> (Bezeichnung, Kategorie, Größe, Shop-Link,
Einzelpreis, Anzahl, Gesamtpreis = Einzelpreis × Anzahl, <i>Für Parcoursplanung verwenden</i>),
<b>Notizen</b>, <b>Dokumente</b> (z. B. Rechnung oder Foto) und <b>Reparaturkosten</b>
(Datum, Beschreibung, Kosten, durchgeführt von, optional <b>Rechnung</b>). Die Rechnung liegt in
den Dokumenten des Artikels und ist in der Reparatur verlinkt (Spalte <i>Rechnung</i>, Doppelklick
oder <b>Rechnung öffnen</b>); löschst du das Dokument, wird der Link leer. Reparaturkosten zählen
nicht zum Inventarwert. Import und Export sind möglich.</p>
<p>Ein Artikel kann <b>aktiv</b> oder <b>inaktiv</b> sein. Die Checkbox
<i>Aktives Inventar anzeigen</i> unten links ist standardmäßig angehakt und zeigt dann nur
aktive Artikel; ohne Haken siehst du alle. Inaktive Artikel zählen nicht zum Inventarwert und
stehen nicht im Parcoursplan zur Auswahl.</p>
<a name="inventarkategorien"></a><p>Die <b>Kategorien</b> (Dropdown im Artikel und Filter der Liste) pflegst du unter Einstellungen → Turnierverwaltung → Allgemein (Anlegen, Umbenennen, Löschen). Eine Kategorie
lässt sich nur löschen, wenn keine Artikel mehr darin sind; sonst bietet das Programm an, die
Artikel in eine andere Kategorie zu verschieben.</p>
<p>Artikel mit <i>Für Parcoursplanung verwenden</i> stehen im Parcoursplan eines Turniers zur
Auswahl.</p>
<h3>Kalender</h3>
<p>Der Kalender zeigt alle Turniere als farbige Badges (Farbe je Phase). Mit den
Buttons <b>Jahr</b>, <b>Monat</b>, <b>Woche</b> und <b>Tag</b> wechselst du die
Ansicht; BowTally merkt sich die zuletzt gewählte. <b>◀</b>, <b>Heute</b> und
<b>▶</b> navigieren in der Zeit.</p>
<p>Die Jahresansicht zeigt alle zwölf Monate; Tage mit Turnieren sind farblich
hervorgehoben. Ein Klick auf einen Monatsnamen springt direkt in die Monatsansicht.
Fährst du mit der Maus über ein Turnier, erscheint eine Vorschau mit
<b>Turnier öffnen →</b>; ein Klick auf das Badge öffnet das Turnier direkt.</p>
<p><b>ICS exportieren</b> schreibt alle Turniere in eine Kalenderdatei
(<code>.ics</code>) im Exportordner, die du in andere Kalender-Apps importieren
kannst.</p>
<h3>Eingebaute Regelwerke und ihre Quellen</h3>
<p>Die Gleichstandsregeln der Standard-Regelwerke folgen den Regelwerken der Verbände
(Stand der Recherche: WA 2026, IBO, IFAA 2021/22, DBSV WKO 2024):</p>
<ul>
  <li><b>WA Halle 18&nbsp;m / 25&nbsp;m</b>: meiste 10er, dann 9er, dann gleicher Rang (kein X)</li>
  <li><b>WA 3D</b>: meiste 11er, dann 10er, dann gleicher Rang</li>
  <li><b>IBO 3D</b> (Hunter, Standard, 12-Ring): meiste Treffer in der höchsten Wertung; für die
      vorderen Plätze ist ein Stechen vorgeschrieben</li>
  <li><b>DBSV 3D-Waldrunde</b>: meiste 15er, dann gleicher Rang; Kills werden nur gezählt</li>
  <li><b>IFAA Feld</b>: bei Gleichstand Stechen für jede Auszeichnung</li>
</ul>
<p>Regelwerke ohne belegbare Quelle (ASA&nbsp;3D, NFAA&nbsp;3D, 3D&nbsp;Standard&nbsp;3-Pfeil,
DBSV&nbsp;3D-Jagdrunde, Blasrohr Standard) gibt es nicht mehr als Standard; Turniere, die eines davon
nutzten, behalten es als eigenes Regelwerk. Standard für neue Turniere ist „3D Hunter (IBO)“. Wer
eine andere Regel braucht, kopiert ein Regelwerk und passt die Kopie an.</p>
<h3>Regelwerke exportieren und importieren</h3>
<p>Der Export (Excel, OpenDocument, CSV) enthält je Regelwerk eine lesbare Zeile mit
Bezeichnung, Beschreibung, Disziplin, Schüssen je Ziel, Nachschuss, den Zonen und den
Ja/Nein-Spalten für Kills, X-Treffer, Treffer in der höchsten Wertung (auch „zuerst“) und
Stechen. Die Zonen stehen als
Text: <code>Kill-Zone = 11 [Kill]; Körper = 8; Miss = 0 [Miss]</code> (Name = Punkte, der Typ
in eckigen Klammern ist optional). Dieselbe Tabelle lässt sich wieder importieren; ältere
Dateien mit JSON-Zonen werden weiterhin gelesen.</p>
<h3>Regelwerk-Standard</h3>
<p>In der Liste der Regelwerke lässt sich über <b>Als Standard setzen</b>
(Rechtsklick → Kontextmenü) ein Regelwerk als Standard markieren (⭐).
Beim Anlegen neuer Turniere wird dieses Regelwerk automatisch vorausgewählt.</p>
"""),
    ("Helfer", """
<h2>Helfer</h2>
<h3>Helfer im Turnier</h3>
<p>Im geöffneten Turnier zeigt der Tab <b>Helfer</b> die Einsätze dieses
Turniers: Name, Aufgabe, Von, Bis, Bestätigt und Kontaktdaten. Es gibt zwei
Wege, einen Helfer hinzuzufügen:</p>
<ul>
  <li><b>Aus Mitgliederkartei</b> weist aktive Mitglieder zu, die als
      <i>Turnierhelfer</i> markiert sind (bereits zugewiesene werden nicht
      angeboten). Name und Kontaktdaten kommen aus der Mitgliederkartei und
      lassen sich hier nicht ändern.</li>
  <li><b>Neuer Helfer</b> legt eine Person nur für dieses Turnier an – ohne
      Eintrag in der Mitgliederkartei und ohne Helferhistorie.</li>
</ul>
<p>Im Einsatz-Dialog trägst du Aufgabe und Zeit ein und kannst
<i>Bestätigung versendet</i> abhaken.</p>
<p>Im Kontextmenü: <b>Bestätigung per E-Mail senden</b> (öffnet die Helfer-Vorlage als
E-Mail, nur mit E-Mail-Adresse), <b>Bestätigung per WhatsApp senden</b> (nur mit gültiger
Telefonnummer), <b>Als bestätigt markieren</b>,
<b>Bestätigung zurücksetzen</b> und <b>Entfernen</b>.
<b>Helferliste drucken</b> erstellt eine PDF-Liste, <b>Exportieren</b> eine
Tabelle (CSV, Excel, OpenDocument) – ohne Bankdaten.</p>
<p>Sobald die <b>Ergebnisliste erstellt</b> oder das Turnier abgeschlossen ist, sind
die Helfer gesperrt: Anlegen, Zuweisen, Bearbeiten und Entfernen sind nicht mehr
möglich; Drucken, Exportieren und das Senden der Bestätigung bleiben verfügbar.</p>
<h3>Helferhistorie</h3>
<p>Beim Abschluss des Turniers (Phase <i>Abgeschlossen</i>) wird für jedes
Mitglied unter den Helfern automatisch ein Eintrag in dessen Helferhistorie
geschrieben: Turnier, Datum, Aufgabe und – wenn Von und Bis eingetragen sind –
die Stunden. Ein erneuter Abschluss erzeugt keine Dopplungen; wird das Turnier
wieder geöffnet, verschwinden die automatischen Einträge. Von Hand ergänzte
Einträge bleiben immer erhalten. Ein von Hand ergänzter Einsatz lässt sich über
<i>Turnier (optional)</i> mit einem bestehenden Turnier verknüpfen (Name und Datum werden
vorbelegt); pro Mitglied und Turnier gibt es nur einen Eintrag. Ein verknüpfter manueller Einsatz
bleibt bearbeitbar, die automatischen Einträge bleiben unverändert.</p>
"""),
    ("Mitglieder", """
<h2>Mitglieder</h2>
<p>Das Modul <b>Mitglieder</b> ist die Mitgliederkartei des Vereins. Jedes
Mitglied hat eine eindeutige <b>Mitgliedsnummer</b> und bis zu fünf Tabs:</p>
<ul>
  <li><b>Basisdaten</b> – Name, Adresse, Kontakt, Eintritt, <i>Einwilligung Datenverarbeitung</i>
      (mit Datum: erscheint beim Ankreuzen, vorbelegt mit heute), <i>Info per E-Mail</i>,
      <i>Ist Helfer</i> und Status <i>Aktiv</i> / <i>Gekündigt</i></li>
  <li><b>Bankverbindung</b> – Kontoinhaber, IBAN, BIC, Bank und
      SEPA-Lastschrift</li>
  <li><b>Helferhistorie</b> – bisherige Helfereinsätze; der Tab erscheint nur bei <i>Ist Helfer</i></li>
  <li><b>Notizen</b> – Freitext (das Feld nimmt die halbe Höhe ein)</li>
  <li><b>Dokumente</b> – Dateien (z.&nbsp;B. Mitgliedsantrag). Dateien werden in den
      Datenordner von BowTally kopiert, lassen sich öffnen und entfernen und sind im Backup
      enthalten. Hinzufügen geht erst nach dem ersten Speichern.</li>
</ul>
<p>Nur aktive Mitglieder mit gesetztem Kennzeichen <i>Ist Helfer</i> lassen sich
im Turnier über <b>Aus Mitgliederkartei</b> als Helfer zuweisen.</p>
<p><b>Datenschutz:</b> Bankdaten erscheinen in keinem Export und in keiner
Liste. Sie sind nur Bestandteil des passwortgeschützten Backups.</p>
<p><b>Datenauskunft:</b> Möchte ein Mitglied wissen, welche Daten über es gespeichert sind,
wählt man das Mitglied aus und klickt auf <b>Datenauskunft per E-Mail senden</b> (nur mit
hinterlegter E-Mail-Adresse) oder <b>Datenauskunft per WhatsApp senden</b> (nur mit gültiger
Telefonnummer). Es öffnet sich ein Mailentwurf mit allen gespeicherten Daten; die IBAN ist bis
auf die letzten vier Stellen durch Sternchen ersetzt. Der Text lässt sich unter
<b>Einstellungen &rarr; E-Mail-Vorlagen &rarr; Datenauskunft</b> anpassen (Platzhalter
<code>{daten}</code>).</p>
"""),
    ("Dashboard & Logbuch", """
<h2>Dashboard &amp; Logbuch</h2>
<h3>Dashboard</h3>
<p>Ohne geöffnetes Turnier zeigt das Dashboard Kacheln für
<i>Aktive Turniere</i>, <i>Nächstes Turnier</i>, <i>Turnierarchiv</i>,
<i>Schützen</i>, <i>Regelwerke</i>, <i>Bogenklassen</i>, <i>Helfer</i>,
<i>Inventar</i> (mit Gesamtwert) und <i>Kalender</i> mit Direktlinks. Die Kacheln lassen sich
per Drag-and-Drop umsortieren; die Reihenfolge bleibt erhalten.</p>
<h3>Turnier-Dashboard</h3>
<p>Mit geöffnetem Turnier (<b>Turnier-Dashboard</b> in der Seitenleiste) zeigt
es Karten für <b>Teilnehmer</b> (inklusive Hinweis „Ausschreibung veraltet“
mit <b>Neu generieren</b>), <b>Einnahmen</b>, <b>Aktuelle Phase</b> (nächste
Aufgabe, Notizen und Link <b>Zum Leitfaden</b>), <b>Ergebnisfortschritt</b>
(ab der Phase Schießen), <b>Klassen</b> und <b>Zeitplan</b> (Anmeldefrist,
Turnierdatum, Einschreibung ab, Schießbeginn mit Countdown). Die Karte
<b>Material</b> zeigt getrennt die <b>Kosten Einmalartikel</b> (echte Zusatzkosten dieses
Turniers) und den <b>Warenwert Bestandsinventar</b> (angeforderte Menge × Einzelpreis der
verwendeten Inventarartikel). Ein Klick auf eine Karte öffnet die passende Ansicht.</p>
<h3>Logbuch</h3>
<p>Das <b>Logbuch</b> protokolliert Aktivitäten als Tabelle mit einer Zeile je Eintrag
(Zeit, Typ, Meldung, Kontext). Du kannst nach Turnier,
Zeitraum (Gesamter Zeitraum, Heute, 7 oder 30 Tage), Typ und Text filtern sowie
mit <b>Ältere laden …</b> in älteren Einträgen blättern. Geführt werden
Ergebniseingaben, Phasenwechsel, Backups und Eincheckungen.</p>
"""),
    ("Regelwerke & Turnierregeln", """
<h2>Regelwerke &amp; Turnierregeln</h2>
<p>Das Modul <b>Regelwerke</b> hat zwei Tabs: <b>Regelwerke</b> (Punktverteilung)
und <b>Turnierregeln</b> (globale Texte).</p>
<h3>Regelwerke</h3>
<p>Ein Regelwerk definiert, wie viele Schüsse je Scheibe erlaubt sind und wie
viele Punkte je Trefferzone vergeben werden. Standard-Regelwerke
(Chip <i>Standard</i>) sind schreibgeschützt – über <b>Kopieren</b> erstellst
du eine anpassbare Kopie.</p>
<p>Jedes Regelwerk hat eine <b>Disziplin</b> (3D-Parcours oder Scheibe). Unter
<b>Zusatzwertungen und Gleichstand</b> schaltest du ein, ob <b>Kills</b> (nur 3D-Parcours) und
<b>X-Treffer</b> (nur Scheibe) gezählt werden und ob bei gleicher Punktzahl die höhere Anzahl
gewinnt. Gezählt werden Zonen mit dem passenden <b>Typ</b> in der Zonenliste.</p>
<h3>Regelwerk-Standard</h3>
<p>In der Liste der Regelwerke lässt sich über <b>Als Standard setzen</b>
(Rechtsklick → Kontextmenü) ein Regelwerk als Standard markieren (⭐).
Beim Anlegen neuer Turniere wird dieses Regelwerk automatisch vorausgewählt.</p>
<h3>Turnierregeln (globale Texte)</h3>
<p>Der Tab <b>Turnierregeln</b> enthält zwei Texte, die für alle Turniere
gelten:</p>
<ul>
  <li><b>Allgemeine Turnierregeln</b></li>
  <li><b>Teilnahmebedingungen</b></li>
</ul>
<p><b>Speichern</b> ist nur aktiv, wenn du etwas geändert hast.
<b>Turnierregeln exportieren</b> erstellt einen Aushang als PDF mit den
allgemeinen Turnierregeln; ist ein Turnier geöffnet, steht dessen Name, Datum,
Ort und Veranstalter darüber. Die <b>Teilnahmebedingungen</b> erscheinen als
eigene Seite am Ende der Ausschreibung (sofern der Text gepflegt ist).</p>
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
<a name="bankdaten"></a><h3>Bankdaten</h3>
<p>IBAN, BIC und Verwendungszweck-Vorlage für Startgebühren-Überweisungen.
Im Verwendungszweck können Platzhalter genutzt werden: <code>{name}</code> (Vor- und
Nachname des Schützen) und <code>{bow_class}</code> (Bogenklasse), siehe „Referenz“.</p>
<a name="allgemein"></a><h3>Turnierverwaltung → Allgemein</h3>
<p><i>Automatisch neu berechnen</i> (Rang), <i>Warteliste bei Vollbelegung</i> und
<i>Teilnehmer pro Gruppe</i> (Standard 5; daraus berechnet der Turnier-Assistent die
Startgruppen). Die
Gleichstandsregeln stellst du je Regelwerk ein. Im Block <b>Druck</b> stellst du
Papiergröße (A4, A5, A3, Letter), Format (Hoch- oder Querformat), Vereinslogo
und Einzelwertung je Scheibe auf Ausdrucken ein. Im Block <b>Inventarkategorien</b>
pflegst du die Kategorien des Inventars.</p>
<a name="textvorlagen"></a><h3>Turnierverwaltung → Textvorlagen</h3>
<p>Textvorlagen für Ausschreibungen: Parcours-Beschreibung, Überweisungshinweis,
Gruppenhinweis und Wichtige Hinweise. Sie werden im Turnier-Assistenten als Vorgabe
übernommen und dort je Turnier angepasst.</p>
<a name="email-vorlagen"></a><h3>Turnierverwaltung → E-Mail-Vorlagen</h3>
<p>Betreff und Text für die acht E-Mail-Vorlagen (Anmeldebestätigung, Zahlungserinnerung,
Startunterlagen, Ergebnisversand, Wartelisten-Nachrücker, Helfer-Bestätigung,
Datenauskunft und Turnier-Ankündigung). Platzhalter wie <code>{name}</code> oder
<code>{turniername}</code> schreibst du in geschweiften Klammern; welche in welcher Vorlage
verfügbar sind, steht in der „Referenz“ unter <i>E-Mail-Vorlagen</i>. Mehr zum Versand siehe
„E-Mail-Funktionen“.</p>
<h3>Turnierverwaltung → WhatsApp-Vorlagen</h3>
<p>Je ein Text für die sechs WhatsApp-Vorlagen (Anmeldebestätigung, Zahlungserinnerung,
Startunterlagen, Wartelisten-Nachrücker, Helfer-Bestätigung, Datenauskunft). Es gibt keinen
Betreff; die Platzhalter sind dieselben wie bei den E-Mail-Vorlagen. Mehr siehe „WhatsApp“.</p>
<h3>System → Allgemein</h3>
<p><b>Update-Prüfung</b> (Beim Start nach Updates suchen, <b>Jetzt prüfen</b>) und
der <b>Standard-Exportpfad</b> für erzeugte Dateien (leer = Downloads-Ordner),
siehe „Backup &amp; Updates“. Im Block <b>Oberfläche</b> stellst du Sprache und
Schriftart ein. Zur Wahl stehen die mitgelieferten Schriften <b>Open Sans</b>
(Standard), <b>Inter</b> und <b>Source Sans 3</b> sowie <b>Segoe UI</b>. Die Schrift gilt für
die Oberfläche (nach einem Neustart: nach dem Speichern fragt BowTally, ob es sofort neu
starten soll) und sofort für PDFs. Die Schriftdateien gehören zum
Programm und stehen nicht im Backup; die Auswahl selbst ist im Backup enthalten. Die Lizenzen
stehen in <code>docs/THIRD-PARTY-NOTICES.md</code>.</p>
<h3>System → Design</h3>
<p><b>Darstellung</b> System, Hell oder Dunkel (Dark Mode), Markenfarben und
individuelle Farben für das helle und dunkle Theme, <b>Vorschau anwenden</b> und
<b>Zurücksetzen auf Standard</b>.</p>
<h3>Regelwerke</h3>
<p>Regelwerke definieren, wie viele Schüsse je Scheibe erlaubt sind und
wie viele Punkte je Trefferzone vergeben werden. Standard-Regelwerke
(Chip <i>Standard</i>) sind schreibgeschützt – über <b>Kopieren</b> erstellst
du eine anpassbare Kopie.</p>
<p>Jedes Regelwerk hat eine <b>Disziplin</b> (3D-Parcours oder Scheibe). Unter
<b>Zusatzwertungen und Gleichstand</b> schaltest du ein, ob <b>Kills</b> (nur 3D-Parcours) und
<b>X-Treffer</b> (nur Scheibe) gezählt werden und ob bei gleicher Punktzahl die höhere Anzahl
gewinnt. Gezählt werden Zonen mit dem passenden <b>Typ</b> in der Zonenliste.</p>
<h3>Bogenklassen</h3>
<p>Bogenklassen gruppieren Schützen für die Wertung (z. B. Recurve, Compound).
Auch Standard-Klassen sind schreibgeschützt. Reihenfolge per Drag-and-Drop.</p>
<h3>Backup</h3>
<p>Siehe „Backup &amp; Updates“: automatisches Backup beim Beenden, Speicherort
(Lokal / Netzwerk / Nextcloud), Aufbewahrungsdauer und Wiederherstellung aus
einer JSON-Datei.</p>
<h3>Navigation</h3>
<p>Unter Einstellungen → System → Allgemein → <b>Navigation</b> lässt sich die Reihenfolge der
Einträge in der Seitenleiste per Drag-and-Drop anpassen. Die Änderungen
werden nach einem <b>Neustart</b> der App wirksam; nach dem Speichern fragt BowTally, ob es
sofort neu starten soll.</p>
<a name="erweitert"></a><h3>System → Erweitert</h3>
<p>Der <b>Logging-Modus</b> bestimmt, wie ausführlich BowTally in die Logdatei
<code>app.log</code> schreibt: <b>Info</b> (Standard), <b>Warnung</b> (nur Warnungen und
Fehler) oder <b>Debug</b>. Debug schreibt sehr viele Details, kann personenbezogene Daten
und Dateipfade enthalten und lässt die Datei schnell wachsen; BowTally fragt vor dem
Aktivieren nach. Nutze Debug nur auf Anweisung des Supports. Die Änderung gilt sofort
nach dem Speichern. Mit <b>Logfile öffnen</b> öffnest du <code>app.log</code> im
Standardprogramm.</p>
"""),
    ("E-Mail-Funktionen", """
<h2>E-Mail-Funktionen</h2>
<p>BowTally versendet keine E-Mails selbst: Es öffnet eine vorbereitete Nachricht in deinem
Standard-Mailprogramm, die du prüfst und abschickst.</p>
<h3>Vorlagen und Platzhalter</h3>
<p>Unter Einstellungen → Turnierverwaltung → <b>E-Mail-Vorlagen</b> pflegst du Betreff und Text
für sieben Vorlagen: Anmeldebestätigung, Zahlungserinnerung, Startunterlagen, Ergebnisversand,
Wartelisten-Nachrücker, Helfer-Bestätigung und Turnier-Ankündigung. Platzhalter schreibst du in
geschweiften Klammern, z. B. <code>{name}</code> (Liste siehe „Referenz“). Unbekannte
Platzhalter bleiben im Text stehen.</p>
<h3>Wo werden Mails vorbereitet?</h3>
<ul>
  <li><b>Teilnehmer</b> (Rechtsklick): <i>Anmeldebestätigung / Zahlungserinnerung /
      Startunterlagen per E-Mail senden</i>. Bei mehreren Teilnehmern fragt BowTally vorher nach, weil je
      Person ein Mail-Fenster geöffnet wird.</li>
  <li><b>Anmeldung bestätigen</b> fragt anschließend, ob die Bestätigungsmail geöffnet werden soll.</li>
  <li><b>Warteliste</b>: Nach dem Nachrücken öffnet <b>Benachrichtigen</b> eine Liste, aus der du
      mit <b>Benachrichtigung per E-Mail senden (n)</b> die Wartelisten-Mail an ausgewählte
      Personen öffnest.</li>
  <li><b>Helfer</b> (Rechtsklick): <i>Bestätigung per E-Mail senden</i></li>
  <li><b>Mitglieder</b> (Rechtsklick): <i>Datenauskunft per E-Mail senden</i></li>
  <li><b>Auswertung</b>: <b>Ergebnisse per E-Mail senden</b></li>
  <li><b>Ankündigung</b> nach dem Erzeugen der Ausschreibung</li>
</ul>
<p>Hat ein Teilnehmer oder Helfer keine E-Mail-Adresse, meldet BowTally das; ist eine Vorlage leer,
erscheint ein Hinweis auf Einstellungen → E-Mail-Vorlagen.</p>
<h3>Ankündigungs-Mail</h3>
<p>Erstellst du die Ausschreibung über den Leitfaden (<b>PDF generieren</b>) oder das Dashboard
(<b>Neu generieren</b>), fragt BowTally, ob die <b>Turnier-Ankündigung</b> versendet werden soll –
sofern aktive Schützen mit der Option <i>Bei neuen Turnieren per E-Mail benachrichtigen</i> und
E-Mail-Adresse existieren. Die Mail wird mit der Ausschreibung (PDF) im Anhang geöffnet; die
Empfänger stehen im Blindkopie-Feld (BCC).</p>
<h3>Ergebnisversand</h3>
<p><b>Ergebnisse per E-Mail senden</b> (erst nach „Ergebnisliste erstellen“) öffnet eine Liste mit Rang und
Punkten. Vorausgewählt sind Teilnehmer mit der Option <i>Ergebnisversand per E-Mail</i>; Teilnehmer
ohne E-Mail-Adresse sind ausgegraut. <b>Ergebnisse per E-Mail senden (n)</b> öffnet je Auswahl eine Mail mit der
<b>Ergebnisliste im Anhang</b>.</p>
<h3>Anhang-Mechanismus (.eml)</h3>
<p>Ein <code>mailto:</code>-Link kann keine Dateien enthalten. Bei Mails mit Anhang erzeugt BowTally
daher einen <b>.eml-Entwurf</b> (als „unversendet“ markiert) mit dem PDF und öffnet ihn im
Standard-Mailprogramm. Das Mailprogramm muss <code>.eml</code>-Dateien als bearbeitbaren Entwurf
öffnen können. Mails ohne Anhang werden als normaler <code>mailto:</code>-Link geöffnet.</p>
"""),
    ("WhatsApp", """
<h2>WhatsApp</h2>
<p>Neben der E-Mail kann BowTally einen <b>WhatsApp-Chat mit vorausgefülltem Text</b> öffnen
(Click-to-Chat über <code>wa.me</code>). BowTally sendet dabei nichts: Der Link öffnet WhatsApp
Desktop bzw. WhatsApp Web, dort prüfst und sendest du die Nachricht selbst.</p>
<h3>Wo gibt es WhatsApp?</h3>
<ul>
  <li><b>Teilnehmer</b> (Rechtsklick): <i>Anmeldebestätigung / Zahlungserinnerung /
      Startunterlagen per WhatsApp senden</i></li>
  <li><b>Warteliste</b>: im Dialog <b>Benachrichtigen</b> der Button <b>Benachrichtigung per WhatsApp senden (n)</b></li>
  <li><b>Helfer</b> (Rechtsklick): <i>Bestätigung per WhatsApp senden</i></li>
  <li><b>Mitglieder</b> (Rechtsklick): <i>Datenauskunft per WhatsApp senden</i></li>
</ul>
<p>Die Einträge erscheinen bzw. sind aktiv, wenn eine gültige Telefonnummer hinterlegt ist.
Ergebnisversand und Turnier-Ankündigung gibt es nur per E-Mail, weil WhatsApp-Links keine
Anhänge (PDF) übertragen können.</p>
<a name="whatsapp-app"></a><h3>App oder WhatsApp Web</h3>
<p>Unter Einstellungen → Turnierverwaltung → WhatsApp-Vorlagen legst du mit <b>WhatsApp öffnen
mit</b> fest, wohin der Link führt:</p>
<ul>
  <li><b>WhatsApp-App (wa.me)</b> (Standard) – der Browser öffnet <code>wa.me</code> und übergibt
      an WhatsApp Desktop.</li>
  <li><b>WhatsApp Web im Browser</b> – öffnet <code>web.whatsapp.com</code> direkt; beim ersten
      Mal meldest du dich dort per QR-Code an.</li>
</ul>
<p>Meldet Windows beim Öffnen „Der Datei ist keine App zum Ausführen dieser Aktion zugeordnet“,
ist dem Link <code>whatsapp://</code> keine App zugeordnet – auch wenn WhatsApp Desktop installiert
ist. Die Zeile <b>Linktyp whatsapp</b> in den WhatsApp-Vorlagen zeigt, ob eine App zugeordnet
ist. <b>App zuordnen …</b> öffnet die Windows-Einstellungen direkt bei den
Standard-Apps von WhatsApp Desktop: Dort beim Eintrag <code>WHATSAPP</code> die App WhatsApp
wählen und zu BowTally zurückkehren – der Status aktualisiert sich. (Windows erlaubt Programmen
nicht, Standard-Apps selbst festzulegen.) Alternativ <b>WhatsApp Web im Browser</b> wählen.</p>
<h3>Telefonnummern</h3>
<p>BowTally wandelt die Nummer lokal in das internationale Format um: Leerzeichen, Klammern,
Binde- und Schrägstriche fallen weg, eine führende <code>0</code> wird zu <code>+49</code>,
<code>00</code> zu <code>+</code>, <code>+49 (0) …</code> wird zu <code>+49 …</code>.
Beispiele: <code>0171 1234567</code> und <code>+49 171 1234567</code> ergeben
<code>+491711234567</code>. Nummern mit Buchstaben, zu kurze Nummern oder Nummern ohne
Vorwahl (weder <code>0</code> noch <code>+</code>) gelten als ungültig; BowTally meldet das.</p>
<h3>Mehrere Empfänger</h3>
<p>WhatsApp zeigt immer nur einen Chat – jeder neue Link würde den vorigen ersetzen. Bei mehreren
Empfängern öffnet BowTally deshalb einen Dialog, in dem du die Empfänger nacheinander
abarbeitest: <b>WhatsApp öffnen</b>, in WhatsApp senden, <b>Als gesendet markieren</b>,
<b>Nächster Empfänger</b>. Der Status je Zeile ist <i>Offen</i>, <i>Geöffnet</i>,
<i>Bestätigt</i> oder <i>Übersprungen</i> (auch für Empfänger ohne gültige Nummer). BowTally
schaltet nie selbst weiter, und <i>Bestätigt</i> setzt nur deine Markierung – ein geöffneter
Chat heißt nicht, dass die Nachricht gesendet wurde. Der Status wird nicht gespeichert.</p>
<h3>Vorlagen</h3>
<p>Die Texte pflegst du unter Einstellungen → Turnierverwaltung → <b>WhatsApp-Vorlagen</b>
(nur Text, kein Betreff). Es gelten die Platzhalter der E-Mail-Vorlagen außer
<code>{logo}</code> (siehe „Referenz“). Ist eine Vorlage leer oder fehlerhaft, erscheint ein
Hinweis; Platzhalter ohne Wert bleiben im Text stehen und werden gemeldet.</p>
<h3>Datenschutz</h3>
<p>Anders als <code>mailto:</code> sind <code>wa.me</code> und <code>web.whatsapp.com</code>
Links auf Domains von Meta.
Name, Rufnummer und Nachrichtentext gehen dabei im Rahmen des von dir ausgelösten Browser- bzw.
App-Aufrufs an WhatsApp – nicht durch BowTally selbst. Das gilt besonders für die
<b>Datenauskunft</b>, die persönliche Daten enthält.</p>
"""),
    ("Import & Export", """
<h2>Import &amp; Export</h2>
<h3>Import</h3>
<p>Schützen, Helfer, Bogenklassen, Regelwerke, Inventar und Teilnehmer lassen sich per
<b>Importieren</b> aus CSV, Excel (<code>.xlsx</code>) oder OpenDocument (<code>.ods</code>)
einlesen (bei Teilnehmern über das ⋮-Menü). Der Import-Dialog führt durch:</p>
<ul>
  <li><b>Spalten-Zuordnung</b> – BowTally ordnet gängige Spaltenbezeichnungen automatisch zu;
      Pflichtfelder sind mit * markiert</li>
  <li><b>Vorschau</b> der ersten Zeilen und <b>Validierung</b>: fehlerhafte Zeilen werden
      gemeldet und übersprungen</li>
  <li><b>Duplikate</b>: Überspringen, Aktualisieren oder Immer neu</li>
</ul>
<p>Beim Teilnehmerimport prüft BowTally, ob die maximale Teilnehmerzahl überschritten wird.</p>
<h3>Export</h3>
<p>Der Button <b>Exportieren</b> bietet Excel, OpenDocument und CSV. Ist ein Filter aktiv, kannst du
zwischen <i>Alle Datensätze</i> und <i>Nur gefilterte</i> wählen. CSV-Dateien verwenden das
Semikolon als Trennzeichen (UTF-8); bestehen die Daten aus mehreren Tabellenblättern, entstehen
mehrere CSV-Dateien. Nach dem Export bietet ein Hinweis <b>Öffnen</b> an.</p>
<p>Verfügbar ist der Export u. a. bei Schützen, Helfern, Bogenklassen, Regelwerken, Inventar und
der Rangliste (zusätzlich als PDF). In der Phase <i>Abgeschlossen</i> exportiert
<b>Alle Turnierdaten exportieren</b> (Leitfaden) Teilnehmer, Ergebnisse, Rangliste,
Startgebühren und Notizen.</p>
<h3>PDF-Dokumente</h3>
<p>Ausschreibung, Listen, Pläne, Urkunden und Ergebnisliste werden als PDF im
<b>Standard-Exportpfad</b> abgelegt (Einstellungen → System → Allgemein; leer =
Downloads-Ordner).</p>
"""),
    ("Backup & Updates", """
<h2>Backup &amp; Updates</h2>
<h3>Backup</h3>
<p>Unter Einstellungen → System → <b>Backup</b> stellst du ein:</p>
<ul>
  <li><b>Automatisches Backup beim Beenden der App</b> und die <b>Aufbewahrungsdauer</b>
      (1–365 Tage); ältere Backups werden nach einer Sicherung automatisch gelöscht</li>
  <li><b>Speicherort</b>: <i>Lokal</i> (Ordner), <i>Netzwerk</i> (NAS / Freigabe, optional mit
      Anmeldung) oder <i>Nextcloud</i> (Server-URL, Benutzer, Passwort, Zielpfad). Nextcloud
      ist nur ein Speicherziel für Backups: BowTally lädt die Datei hoch, gleicht aber keine
      Daten ab und lädt nichts herunter; zum Wiederherstellen holst du die ZIP-Datei selbst
      von Nextcloud</li>
  <li><b>Verbindung testen</b> prüft den gewählten Speicherort, <b>Backup jetzt erstellen</b>
      sichert sofort</li>
</ul>
<a name="backup-passwort"></a><p>Backups sind ZIP-Dateien und <b>passwortgeschützt</b>: Das Passwort ist Pflicht, wird bei
jeder Wiederherstellung benötigt und lässt sich nicht wiederherstellen – bewahre es sicher auf.
Im Backup sind alle Daten enthalten, auch alle Einstellungen (inklusive Logging-Modus,
E-Mail- und WhatsApp-Vorlagen sowie <i>Teilnehmer pro Gruppe</i>), das
Logbuch, Inventar (Kategorien, Artikel, Reparaturen,
Parcours-Material), die Bankdaten sowie die Dokumente von Mitgliedern, Schützen und Inventar
(Ordner <code>member_files</code>, <code>archer_files</code>, <code>inventory_files</code>); sie werden bei
der Wiederherstellung zurückgespielt. Fehlen in einem älteren Backup neuere
Einstellungen, erhalten sie ihre Standardwerte. Das automatische Backup beim
Beenden nutzt den eingestellten Speicherort. Jedes Backup erscheint im Logbuch.</p>
<h3>Wiederherstellung</h3>
<p><b>Backup wiederherstellen</b> → ZIP-Datei wählen und das Backup-Passwort eingeben. <b>Achtung:</b> Die aktuelle Datenbank wird
nach Rückfrage ersetzt – das lässt sich nicht rückgängig machen. Danach klickst du auf <b>Jetzt neu starten</b>, die App startet sich selbst neu.
</p>
<p>Vor jeder Datenbank-Migration (z.&nbsp;B. nach einem Update) legt BowTally automatisch eine
Kopie der Datenbank neben der Datenbankdatei ab (<code>bowtally.db.pre-migration-…</code>).</p>
<p>Backups älterer Versionen lassen sich ebenfalls wiederherstellen: Helfer werden dabei zu
Mitgliedern, eingebaute Regelwerke werden über ihren Namen zugeordnet (nicht mehr mitgelieferte
bleiben nur erhalten, wenn ein Turnier sie nutzt), Regelwerke ohne Disziplin bekommen sie aus ihrem
Namen, und die frühere globale
Einstellung „Tie-Break-Logik“ entfällt (die Regel gilt jetzt je Regelwerk).</p>
<h3>Updates</h3>
<p>Unter Einstellungen → System → Allgemein sucht BowTally auf Wunsch <b>beim Start nach
Updates</b> (<i>Beim Start nach Updates suchen</i>). <b>Jetzt prüfen</b> startet die Suche sofort;
<i>Letzte Prüfung</i> zeigt den Zeitpunkt der letzten erfolgreichen Verbindung.</p>
<p>Gibt es eine neue Version, zeigt ein Dialog die Neuerungen und einen Link zum vollständigen
Changelog. Mit <b>Jetzt aktualisieren</b> lädt BowTally den Installer herunter, prüft die
Prüfsumme (sofern vorhanden) und installiert das Update. Windows fragt dabei nach
Administratorrechten, weil BowTally im Programmverzeichnis installiert ist; lehnst du die
Abfrage ab, bleibt die alte Version unverändert. <b>Später erinnern</b> verschiebt es,
<b>Diese Version überspringen</b> blendet sie aus.</p>
<h3>Fehlermeldungen bei der Update-Prüfung</h3>
<p>Bei einer manuellen Prüfung erscheint „Der Update-Server ist nicht erreichbar. Bitte
Internetverbindung prüfen.“ bei Netzwerkproblemen, bzw. eine Meldung mit dem HTTP-Fehlercode,
wenn der Server mit einem Fehler antwortet. Ist alles aktuell, lautet die Meldung „Kein Update
verfügbar.“ Beim automatischen Start-Check bleiben Fehler ohne Meldung.</p>
<h3>Über BowTally</h3>
<p>Der Eintrag <b>Über BowTally</b> (Seitenleiste unten) enthält Informationen zur Version,
den Lizenztext, das Changelog und die Tastenkürzel.</p>
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
  <tr><td><b>Bearbeiten</b></td><td>Stammdaten im Dialog bearbeiten</td></tr>
  <tr><td><b>Klasse ändern …</b></td><td>Standardklasse für die Auswahl setzen</td></tr>
  <tr><td><b>Als inaktiv markieren</b></td><td>Aus Auswahllisten ausblenden</td></tr>
  <tr><td><b>Löschen</b></td><td>Schützen dauerhaft löschen</td></tr>
</table>
<h3>Regelwerke &amp; Bogenklassen</h3>
<table border="0" cellspacing="0" cellpadding="5" style="border-collapse:collapse;">
  <tr><td><b>Bearbeiten</b></td><td>Im Dialog bearbeiten (Standard-Einträge schreibgeschützt)</td></tr>
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
  <tr><td><b>Gebühr / Klasse / Gruppe zuweisen</b></td><td>Direkte Zuweisung für die Auswahl (Klasse und Gruppe nicht in der Schieß-Phase)</td></tr>
  <tr><td><b>Entfernen</b></td><td>Teilnehmer aus dem Turnier entfernen</td></tr>
</table>
"""),
    ("Referenz", """
<h2>Referenz</h2>
<a name="platzhalter"></a><h3>Platzhalter</h3>
<p>Platzhalter werden in bestimmten Textfeldern durch echte Werte ersetzt.
Schreibe sie immer in geschweiften Klammern: <code>{platzhalter}</code></p>
<p><b>Verwendungszweck (Bankverbindung):</b></p>
<table border="0" cellspacing="0" cellpadding="5" style="border-collapse:collapse;">
  <tr><td><code>{name}</code></td><td>Vor- und Nachname des Schützen</td></tr>
  <tr><td><code>{bow_class}</code></td><td>Bogenklasse des Schützen</td></tr>
</table>
<p><i>Beispiel:</i> <code>3D Turnier 2027, {name}, {bow_class}</code></p>
<a name="platzhalter-email"></a><p><b>E-Mail- und WhatsApp-Vorlagen</b> – verfügbare Platzhalter (in WhatsApp-Vorlagen alle
außer <code>{logo}</code>; in der Helfer-Vorlage zusätzlich <code>{aufgabe}</code>,
<code>{von}</code> und <code>{bis}</code>):</p>
<p><i>Immer verfügbar:</i></p>
<table border="0" cellspacing="0" cellpadding="4" style="border-collapse:collapse;">
  <tr><td><code>{name}</code></td><td>Vor- und Nachname des Teilnehmers / Helfers</td></tr>
  <tr><td><code>{first_name}</code>, <code>{last_name}</code></td><td>Vor- bzw. Nachname</td></tr>
  <tr><td><code>{turniername}</code></td><td>Name des Turniers</td></tr>
  <tr><td><code>{datum}</code></td><td>Turnierdatum (TT.MM.JJJJ)</td></tr>
  <tr><td><code>{anmeldefrist}</code></td><td>Anmeldefrist (TT.MM.JJJJ)</td></tr>
  <tr><td><code>{vereinsname}</code></td><td>Vereinsname aus dem Vereinsprofil</td></tr>
  <tr><td><code>{kontakt_name}</code></td><td>Name der Standard-Kontaktperson (bei der Ankündigung die Turnier-Kontaktperson)</td></tr>
  <tr><td><code>{kontakt_email}</code></td><td>E-Mail-Adresse aus dem Vereinsprofil</td></tr>
  <tr><td><code>{kontakt_telefon}</code></td><td>Telefonnummer aus dem Vereinsprofil</td></tr>
</table>
<p><i>In allen Vorlagen außer der Turnier-Ankündigung:</i></p>
<table border="0" cellspacing="0" cellpadding="4" style="border-collapse:collapse;">
  <tr><td><code>{ort}</code></td><td>Veranstaltungsort des Turniers</td></tr>
  <tr><td><code>{iban}</code></td><td>IBAN aus den Turnier-Bankdaten</td></tr>
  <tr><td><code>{bank_account_holder}</code></td><td>Kontoinhaber aus den Turnier-Bankdaten</td></tr>
  <tr><td><code>{checkin_start_time}</code></td><td>Einschreibung ab (Uhrzeit)</td></tr>
  <tr><td><code>{shooting_start_time}</code></td><td>Schießbeginn (Uhrzeit)</td></tr>
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
<p><i>Nur in der Turnier-Ankündigung:</i></p>
<table border="0" cellspacing="0" cellpadding="4" style="border-collapse:collapse;">
  <tr><td><code>{ort}</code></td><td>Veranstaltungsort des Turniers</td></tr>
  <tr><td><code>{klassen}</code></td><td>Bogenklassen des Turniers</td></tr>
  <tr><td><code>{startgeld}</code></td><td>Startgebühren mit Beträgen</td></tr>
</table>
<p><i>Nur in der Datenauskunft (Mitglieder):</i></p>
<table border="0" cellspacing="0" cellpadding="4" style="border-collapse:collapse;">
  <tr><td><code>{daten}</code></td><td>Alle gespeicherten Daten des Mitglieds (IBAN bis auf die letzten vier Stellen maskiert)</td></tr>
</table>
<h3>Tastenkürzel</h3>
<table border="0" cellspacing="0" cellpadding="5" style="border-collapse:collapse;">
  <tr><td><code>Strg+N</code></td><td>Neu (Schütze, Klasse, Regelwerk, Turnier, Teilnehmer, Helfer, Preis, Walk-in)</td></tr>
  <tr><td><code>Strg+F</code></td><td>Suchfeld der aktuellen Ansicht</td></tr>
  <tr><td><code>Strg+S</code></td><td>Speichern (Seitenpanel, Ergebniseingabe)</td></tr>
  <tr><td><code>Esc</code></td><td>Seitenpanel schließen / Suche leeren / Eingabe verwerfen</td></tr>
  <tr><td><code>F5</code></td><td>Ansicht neu laden</td></tr>
  <tr><td><code>F1</code></td><td>Diese Hilfe</td></tr>
  <tr><td><code>Enter</code></td><td>Ausgewählten Eintrag öffnen / Seitenpanel speichern / Einchecken</td></tr>
  <tr><td><code>Tab / Umschalt+Tab</code></td><td>Ergebniseingabe: nächste / vorherige Scheibe</td></tr>
  <tr><td><code>Enter / ↓ / ↑</code></td><td>Ergebniseingabe: nächster / vorheriger Teilnehmer</td></tr>
</table>
<p>Eine kurze Liste der wichtigsten Kürzel steht auch unter
<b>Über BowTally → Tastenkürzel</b>.</p>
<h3>Backup &amp; Wiederherstellung</h3>
<p>Aktiviere <i>Automatisches Backup beim Beenden der App</i> unter Einstellungen →
System → Backup. Für manuelle Sicherungen: <b>Backup jetzt erstellen</b> (Lokal,
Netzwerk oder Nextcloud je nach gewähltem Speicherort).</p>
<p>Zur Wiederherstellung: <b>Backup wiederherstellen</b> → ZIP-Datei wählen, Passwort eingeben.
<b>Achtung:</b> Die aktuelle Datenbank wird unwiderruflich ersetzt.
Danach mit <b>Jetzt neu starten</b> die App neu starten.</p>
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
        self._help_search.setPlaceholderText(SEARCH_PLACEHOLDER)
        self._help_search.setClearButtonEnabled(True)
        QShortcut(QKeySequence.StandardKey.Find, self, self._help_search.setFocus)
        sidebar_lay.addWidget(self._help_search)

        self._nav = QListWidget()
        self._nav.setObjectName("helpNav")
        for title, _ in _SECTIONS:
            self._nav.addItem(title)
        self._help_results = QListWidget()
        self._help_results.setSpacing(2)
        self._nav_stack = QStackedWidget()
        self._nav_stack.addWidget(self._nav)
        self._nav_stack.addWidget(self._help_results)
        sidebar_lay.addWidget(self._nav_stack, 1)

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
        self._help_results.itemActivated.connect(self._on_help_result)
        self._help_index = self._build_help_index()
        self._help_search_timer = QTimer(self)
        self._help_search_timer.setSingleShot(True)
        self._help_search_timer.setInterval(250)
        self._help_search_timer.timeout.connect(
            lambda: self._do_help_search(self._help_search.text()))
        self._help_search.textChanged.connect(lambda: self._help_search_timer.start())
        self._nav.setCurrentRow(0)
        self._apply_browser_css()
        theme.notifier.changed.connect(self._apply_browser_css)

        close_row = QHBoxLayout()
        close_row.addStretch()
        close_row.addWidget(button("Schließen", self.accept))

        lay = QVBoxLayout(self)
        lay.addLayout(body, 1)
        lay.addLayout(close_row)

    def _build_help_index(self) -> list[dict]:
        index = []
        for section_idx, (section_label, html) in enumerate(_SECTIONS):
            parts = re.split(r'<h3[^>]*>(.*?)</h3>', html, flags=re.IGNORECASE | re.DOTALL)
            for i in range(1, len(parts), 2):
                heading = re.sub(r'<[^>]+>', '', parts[i]).strip()
                content = parts[i + 1] if i + 1 < len(parts) else ''
                text = re.sub(r'<[^>]+>', '', content)
                text = re.sub(r'\s+', ' ', text).strip()
                if not text:
                    continue
                index.append({
                    'section_idx': section_idx,
                    'section_label': section_label,
                    'heading': heading,
                    'text': text,
                    'searchable': f"{section_label} {heading} {text}".lower(),
                })
        return index

    def _do_help_search(self, text: str):
        text = text.strip()
        if len(text) < 2:
            for i in range(self._nav.count()):
                self._nav.item(i).setHidden(False)
            self._nav_stack.setCurrentWidget(self._nav)
            return
        needle = text.lower()
        hits = [e for e in self._help_index if needle in e['searchable']]
        rl = self._help_results
        rl.clear()
        if not hits:
            item = QListWidgetItem("Keine Hilfe-Einträge gefunden")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            rl.addItem(item)
        else:
            for e in hits:
                pos = e['text'].lower().find(needle)
                if pos >= 0:
                    start = max(0, pos - 30)
                    end = min(len(e['text']), pos + 90)
                    excerpt = ('…' if start else '') + e['text'][start:end] + \
                              ('…' if end < len(e['text']) else '')
                else:
                    excerpt = e['text'][:120]
                item = QListWidgetItem(
                    f"{e['section_label']} › {e['heading']}\n{excerpt}")
                item.setData(Qt.ItemDataRole.UserRole, e)
                item.setSizeHint(QSize(0, 56))
                rl.addItem(item)
        self._nav_stack.setCurrentWidget(rl)

    def _on_help_result(self, item: QListWidgetItem):
        e = item.data(Qt.ItemDataRole.UserRole)
        if e is None:
            return
        self._nav.setCurrentRow(e['section_idx'])
        term = self._help_search.text().strip()
        if term:
            QTimer.singleShot(0, lambda: self._highlight_in_browser(term))

    def _highlight_in_browser(self, term: str):
        doc = self._browser.document()
        cursor = doc.find(term)
        yellow = QColor("#FFF176")
        while not cursor.isNull():
            fmt = cursor.charFormat()
            fmt.setBackground(yellow)
            cursor.mergeCharFormat(fmt)
            cursor = doc.find(term, cursor)
        # scroll to first occurrence
        self._browser.find(term)

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

    def show_section(self, title: str, anchor: str = ""):
        """Open a chapter; with `anchor` the view scrolls to that <a name> inside the chapter."""
        for i, (t, _) in enumerate(_SECTIONS):
            if t == title:
                self._nav.setCurrentRow(i)
                self._show_section(i)        # also when the chapter was already selected
                if anchor:
                    QTimer.singleShot(0, lambda: self._browser.scrollToAnchor(anchor))
                break
