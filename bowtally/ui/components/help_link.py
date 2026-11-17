# -*- coding: utf-8 -*-
"""Small link that opens the app help directly at a chapter (and optionally a mark inside it)."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from bowtally.ui import theme


def help_link(section: str, anchor: str = "", text: str = "Mehr dazu in der Hilfe") -> QLabel:
    """`section` is the chapter title in the help, `anchor` an <a name="..."> inside that chapter."""
    label = QLabel(f'<a href="#" style="color: {theme.current()["primary"]}; '
                   f'text-decoration: none;">{text}</a>')
    label.setCursor(Qt.CursorShape.PointingHandCursor)
    label.setToolTip("Hilfe öffnen")
    label.linkActivated.connect(lambda _href: _open_help(label, section, anchor))
    return label


def _open_help(label: QLabel, section: str, anchor: str) -> None:
    from bowtally.ui.dialogs.help_dialog import HelpDialog     # lazy: the help module is large
    dialog = HelpDialog(label.window())
    dialog.show_section(section, anchor)
    dialog.exec()
