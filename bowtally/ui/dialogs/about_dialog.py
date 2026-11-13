# -*- coding: utf-8 -*-
"""About BowTally dialog with sidebar navigation."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPixmap
from PySide6.QtWidgets import (QDialog, QFrame, QHBoxLayout, QLabel, QListWidget,
                                QListWidgetItem, QStackedWidget, QTextBrowser,
                                QVBoxLayout, QWidget)

from bowtally import __version__, config
from bowtally.ui import button, restore_geom, save_geom, theme

GITHUB_URL = "https://github.com/jenskaesler/bowtally"

_SHORTCUTS = [
    ("Strg+N", "Neues Turnier anlegen"),
    ("Strg+F", "Suche öffnen"),
    ("Strg+S", "Speichern"),
    ("F5", "Aktualisieren"),
    ("F1", "Hilfe öffnen"),
]


def _read_file(path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Über BowTally")
        self.resize(820, 560)
        restore_geom(self, "about")
        self.finished.connect(lambda: save_geom(self, "about"))

        t = theme.current()

        # Sidebar
        sidebar = QWidget()
        sidebar.setFixedWidth(200)
        sidebar_lay = QVBoxLayout(sidebar)
        sidebar_lay.setContentsMargins(8, 8, 8, 8)
        sidebar_lay.setSpacing(6)

        hdr_font = QFont()
        hdr_font.setPointSize(8)
        hdr_font.setBold(True)

        self._nav = QListWidget()
        self._nav.setObjectName("helpNav")

        hdr = QListWidgetItem("INFORMATIONEN")
        hdr.setFlags(Qt.ItemFlag.NoItemFlags)
        hdr.setFont(hdr_font)
        hdr.setForeground(QColor(t["text2"]))
        self._nav.addItem(hdr)
        for label in ("Über BowTally", "Lizenz", "Changelog", "Tastenkürzel"):
            self._nav.addItem(QListWidgetItem("  " + label))

        sidebar_lay.addWidget(self._nav, 1)

        vline = QFrame()
        vline.setFrameShape(QFrame.Shape.VLine)
        vline.setFrameShadow(QFrame.Shadow.Sunken)

        self._stack = QStackedWidget()
        self._browsers: list[QTextBrowser] = []
        for factory in (self._make_about, self._make_license,
                        self._make_changelog, self._make_shortcuts):
            self._stack.addWidget(factory())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(sidebar)
        body.addWidget(vline)
        body.addWidget(self._stack, 1)

        close_row = QHBoxLayout()
        close_row.addStretch()
        close_row.addWidget(button("Schließen", self.accept, "primary"))

        lay = QVBoxLayout(self)
        lay.addLayout(body, 1)
        lay.addLayout(close_row)

        self._nav.currentRowChanged.connect(self._on_nav)
        self._nav.setCurrentRow(1)
        theme.notifier.changed.connect(self._refresh_css)

    def _on_nav(self, row: int):
        idx = row - 1  # row 0 is the group header
        if 0 <= idx < self._stack.count():
            self._stack.setCurrentIndex(idx)

    def _browser_css(self) -> str:
        t = theme.current()
        return (
            f"code {{ background: {t['surface']}; border-radius: 3px; "
            f"padding: 1px 4px; font-family: monospace; }}"
            f" h3 {{ border-bottom: 1px solid {t['border']}; padding-bottom: 4px; }}"
            f" table {{ border-collapse: collapse; width: 100%; }}"
            f" td, th {{ border-bottom: 1px solid {t['border']}; padding: 6px 8px; }}"
        )

    def _refresh_css(self):
        css = self._browser_css()
        for b in self._browsers:
            b.document().setDefaultStyleSheet(css)

    def _make_browser(self) -> QTextBrowser:
        b = QTextBrowser()
        b.setOpenExternalLinks(True)
        b.setFrameShape(QFrame.Shape.NoFrame)
        b.document().setDefaultStyleSheet(self._browser_css())
        self._browsers.append(b)
        return b

    def _make_about(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(8)

        icon_path = config.ICON_PATH
        if icon_path.exists():
            lbl = QLabel()
            pix = QPixmap(str(icon_path)).scaled(
                64, 64,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            lbl.setPixmap(pix)
            lay.addWidget(lbl)

        b = self._make_browser()
        b.setHtml(
            f"<h1 style='margin-bottom:4px'>BowTally</h1>"
            f"<p style='margin-top:0;color:gray'>Version {__version__}</p>"
            f"<p>Turnierverwaltung für 3D-Bogensport-Vereine. BowTally unterstützt den gesamten "
            f"Turnierablauf – von der Ausschreibung über die Anmeldung und Einschreibung bis zur "
            f"Ergebnisauswertung und dem PDF-Druck.</p>"
            f"<p><b>Entwickler</b><br>"
            f"Jens Kaesler &lt;<a href='mailto:mail@jens-kaesler.de'>mail@jens-kaesler.de</a>&gt;</p>"
            f"<p><b>Quellcode &amp; Releases</b><br>"
            f"<a href='{GITHUB_URL}'>{GITHUB_URL}</a></p>"
        )
        lay.addWidget(b, 1)
        return w

    def _make_license(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 16, 16, 16)
        b = self._make_browser()
        b.setHtml(
            "<h2>BowTally Non-Commercial Copyleft License</h2>"
            "<p><b>Version 1.0, Oktober 2026</b><br>"
            "Copyright (c) 2026 Jens Kaesler &lt;"
            "<a href='mailto:mail@jens-kaesler.de'>mail@jens-kaesler.de</a>&gt;</p>"
            "<p>BowTally ist freie Software für den nicht-kommerziellen Gebrauch. "
            "Du darfst die Software nutzen, kopieren und für nicht-kommerzielle Zwecke "
            "verändern und weitergeben.</p>"
            "<h3>Nicht-kommerzielle Nutzung</h3>"
            "<p>Eine kommerzielle Nutzung – etwa der Verkauf der Software, die Einbindung "
            "in ein bezahltes Produkt oder die Erbringung kostenpflichtiger Leistungen für "
            "Dritte – ist ohne vorherige schriftliche Genehmigung des Rechteinhabers "
            "nicht gestattet.</p>"
            "<h3>Copyleft (Share-Alike)</h3>"
            "<p>Wenn du eine veränderte Version verteilst oder veröffentlichst, musst du</p>"
            "<ul>"
            "<li>den vollständigen Quellcode öffentlich auf GitHub (oder einer "
            "gleichwertigen Plattform) bereitstellen,</li>"
            "<li>die veränderte Version unter denselben Lizenzbedingungen stellen,</li>"
            "<li>deutlich machen, dass Änderungen vorgenommen wurden, und das Datum "
            "angeben.</li>"
            "</ul>"
            "<h3>Attribution</h3>"
            "<p>Alle Copyright-Hinweise und dieser Lizenztext müssen in allen Kopien "
            "erhalten bleiben.</p>"
            "<h3>Keine Gewährleistung</h3>"
            "<p>Die Software wird „wie besehen“ ohne jede Gewährleistung bereitgestellt. "
            "Der Rechteinhaber haftet nicht für Schäden, die aus der Nutzung entstehen.</p>"
            "<h3>Kündigung</h3>"
            "<p>Bei Verstoß gegen diese Lizenz enden deine Rechte automatisch. Du musst "
            "dann alle Kopien vernichten.</p>"
            "<h3>Kontakt</h3>"
            "<p>Für kommerzielle Lizenzanfragen oder weitergehende Genehmigungen: "
            "<a href='mailto:mail@jens-kaesler.de'>mail@jens-kaesler.de</a></p>"
        )
        lay.addWidget(b, 1)
        return w

    def _make_changelog(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(8)
        b = self._make_browser()
        b.setHtml(
            f"<h2>Changelog</h2>"
            f"<p>Die jeweils aktuelle Version ist <b>{__version__}</b>. "
            f"Hier findest du eine Übersicht der wichtigsten Änderungen.</p>"
            f"<h3>Aktuelle Version – {__version__}</h3>"
            f"<ul>"
            f"<li>E-Mail-Vorlagen neu formuliert und um Platzhalter erweitert "
            f"(unter anderem Startgruppe, Startnummer, Kontakt und Logo).</li>"
            f"<li>Signatur wird automatisch aus den Vereinsdaten zusammengesetzt; "
            f"das Vereinslogo erscheint unter der Mail, wenn eines hinterlegt ist.</li>"
            f"<li>Warteliste steht bei Vollbelegung standardmäßig auf „automatisch“.</li>"
            f"<li>Standardreihenfolge der linken Navigation angepasst.</li>"
            f"<li>Lizenzinformationen und Changelog im Über-Dialog ergänzt.</li>"
            f"</ul>"
            f"<h3>Ältere Versionen</h3>"
            f"<p>Alle Änderungen früherer Versionen findest du im vollständigen "
            f"Changelog:</p>"
            f"<p><a href='https://github.com/jenskaesler/bowtally/blob/main/CHANGELOG.md'>"
            f"CHANGELOG.md auf GitHub</a><br>"
            f"<a href='CHANGELOG.md'>lokale CHANGELOG.md im Installationsverzeichnis</a></p>"
        )
        lay.addWidget(b, 1)
        return w

    def _make_shortcuts(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 16, 16, 16)
        b = self._make_browser()
        rows = "".join(
            f"<tr><td><code>{k}</code></td><td>{v}</td></tr>"
            for k, v in _SHORTCUTS
        )
        b.setHtml(
            "<h2>Tastenkürzel</h2>"
            "<table><tr><th align='left'>Kürzel</th><th align='left'>Aktion</th></tr>"
            + rows + "</table>"
        )
        lay.addWidget(b, 1)
        return w
