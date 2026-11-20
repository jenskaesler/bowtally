# Datenschutzhinweis

## Offline-Betrieb

BowTally arbeitet vollständig lokal. Die Anwendung speichert alle Daten ausschließlich auf dem
Gerät des Nutzers und überträgt ohne explizite Konfiguration keine Daten an externe Server.

Folgende Daten werden lokal gespeichert:

- Teilnehmerdaten (Name, Bogenklasse, Vereinszugehörigkeit)
- Turnierdaten (Bezeichnung, Datum, Phasen, Ergebnisse)
- Vereinsdaten (Name, Adresse, Kontakt, Logo, Bankdaten)
- Einstellungen und Konfiguration

Folgende Daten werden nicht erfasst oder übertragen:

- Nutzungsstatistiken oder Telemetrie
- Absturzberichte
- Lizenzprüfungen
- Automatische Updates oder Versionsprüfungen

## Optionales Nextcloud-Backup

BowTally enthält eine optionale Backup-Funktion für Nextcloud (WebDAV). Diese Funktion ist
standardmäßig deaktiviert. Nextcloud dient ausschließlich als Speicherziel für Backups:
BowTally lädt eine passwortgeschützte Backup-Datei hoch, gleicht aber keine Daten zwischen
Geräten ab und lädt nichts von Nextcloud herunter.

Wenn das Nextcloud-Backup aktiviert wird, gilt:

- Daten werden ausschließlich auf expliziten Nutzerwunsch übertragen.
- Als Ziel wird ausschließlich die vom Nutzer selbst konfigurierte Nextcloud-Instanz verwendet.
- Es findet keine Übertragung an Server des Entwicklers oder Dritter statt.
- Der Nutzer ist für die Absicherung seiner eigenen Nextcloud-Instanz verantwortlich.

## E-Mail und WhatsApp

BowTally versendet selbst keine Nachrichten. E-Mails werden als `mailto:`-Link bzw. `.eml`-Entwurf
im lokalen Mailprogramm geöffnet; das ist ein rein lokaler Aufruf ohne Netzwerkzugriff durch
BowTally.

Die optionale WhatsApp-Funktion öffnet einen Chat über `wa.me` (Click-to-Chat). Anders als
`mailto:` ist `wa.me` ein HTTPS-Link auf eine Domain von Meta: Rufnummer, Name und
Nachrichtentext werden dabei im Rahmen des vom Benutzer selbst ausgelösten Browser- bzw.
App-Aufrufs an WhatsApp übertragen, nicht durch BowTally direkt. Telefonnummern werden
ausschließlich lokal normalisiert, es gibt keinen Validierungsdienst, keinen automatischen
Massenversand und keine Protokollierung der Nachrichten. Gesendet wird jede Nachricht vom
Benutzer selbst in WhatsApp.

## Verantwortlichkeit und DSGVO

BowTally verarbeitet personenbezogene Daten der Turnierteilnehmer ausschließlich lokal auf dem
Gerät des Veranstalters. Der Bogensportverein bzw. Turnierveranstalter ist gemäß DSGVO für die
Verarbeitung dieser Daten verantwortlich.

Empfehlungen für den Umgang mit Teilnehmerdaten:

- Nur die für die Turnierorganisation erforderlichen Daten erfassen.
- Teilnehmerdaten nach Abschluss des Turniers auf Anfrage löschen (Einstellungen: Schütze
  deaktivieren oder löschen, sofern keine Turnierteilnahme verknüpft ist).
- Datenexporte und Backups sicher aufbewahren und bei Bedarf löschen.

## Logs

BowTally schreibt ein lokales Log unter `%APPDATA%\BowTally\app.log`. Das Log enthält
Statusmeldungen, Fehlermeldungen und Backup-Ereignisse. Personenbezogene Daten werden im Log
nicht gespeichert.

## Kontakt

Bei Fragen zum Datenschutz: [mail@jens-kaesler.de](mailto:mail@jens-kaesler.de)
