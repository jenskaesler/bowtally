# -*- coding: utf-8 -*-
"""About BowTally dialog."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout

from bowtally.__version__ import __version__

GITHUB_URL = "https://github.com/jenskaesler/bowtally"


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Über BowTally")
        self.setFixedWidth(480)

        text = QLabel()
        text.setTextFormat(Qt.TextFormat.RichText)
        text.setOpenExternalLinks(True)
        text.setWordWrap(True)
        text.setAlignment(Qt.AlignmentFlag.AlignTop)
        text.setText(f"""
<h2 style='margin-bottom:4px'>BowTally</h2>
<p style='color:gray;margin-top:0'>Version {__version__}</p>

<p>Turnierverwaltung für 3D-Bogensport-Vereine. BowTally unterstützt den gesamten
Turnierablauf – von der Ausschreibung über die Anmeldung und Einschreibung bis zur
Ergebnisauswertung und dem PDF-Druck.</p>

<p><b>Entwickler</b><br>
Jens Kaesler &lt;<a href='mailto:mail@jens-kaesler.de'>mail@jens-kaesler.de</a>&gt;</p>

<p><b>Quellcode &amp; Releases</b><br>
<a href='{GITHUB_URL}'>{GITHUB_URL}</a><br>
<a href='{GITHUB_URL}/releases'>Releases &amp; Changelog</a></p>

<p><b>Lizenz</b><br>
BowTally steht unter einer benutzerdefinierten Lizenz:<br>
&bull; Keine kommerzielle Nutzung ohne ausdrückliche schriftliche Genehmigung.<br>
&bull; Alle Änderungen am Quellcode müssen unter denselben Bedingungen
öffentlich auf GitHub veröffentlicht werden (Copyleft).<br>
Vollständiger Lizenztext: <a href='{GITHUB_URL}/blob/main/LICENSE'>LICENSE</a></p>
""")

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText("Schließen")
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)

        lay = QVBoxLayout(self)
        lay.addWidget(text)
        lay.addWidget(buttons)
