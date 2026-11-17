# -*- coding: utf-8 -*-
"""Modal confirmation for destructive or irreversible actions."""
from PySide6.QtWidgets import QComboBox, QDialog, QHBoxLayout, QLabel, QVBoxLayout

from bowtally.ui import button


class ConfirmDialog(QDialog):
    def __init__(self, parent, title: str, text: str, confirm_text: str = "Löschen",
                 destructive: bool = True, cancel_text: str = "Abbrechen"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(420)
        heading = QLabel(title)
        heading.setObjectName("drawerTitle")
        body = QLabel(text)
        body.setWordWrap(True)
        self.cancel = button(cancel_text, self.reject,
                             tooltip="Nichts ändern" if cancel_text == "Abbrechen" else cancel_text)
        self.ok = button(confirm_text, self.accept, "danger" if destructive else "primary")
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(self.cancel)
        row.addWidget(self.ok)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)
        lay.addWidget(heading)
        lay.addWidget(body)
        lay.addLayout(row)
        # destructive: the safe choice has the focus, Enter does not delete by accident
        (self.cancel if destructive else self.ok).setDefault(True)
        (self.cancel if destructive else self.ok).setFocus()

    @staticmethod
    def ask(parent, title: str, text: str, confirm_text: str = "Löschen",
            destructive: bool = True, cancel_text: str = "Abbrechen") -> bool:
        return ConfirmDialog(parent, title, text, confirm_text, destructive,
                             cancel_text).exec() == QDialog.DialogCode.Accepted


_CANCELLED = object()


def choose(parent, title: str, label: str, options: list[tuple[str, object]],
           current=None, editable: bool = False):
    """Small modal picker. Returns the chosen data (or typed text when editable),
    choose.CANCELLED if the user aborted."""
    dlg = ConfirmDialog(parent, title, label, "Speichern", destructive=False)
    combo = QComboBox()
    combo.setEditable(editable)
    for text, data in options:
        combo.addItem(text, data)
    idx = combo.findData(current)
    if idx >= 0:
        combo.setCurrentIndex(idx)
    elif editable and current:
        combo.setEditText(str(current))
    dlg.layout().insertWidget(2, combo)
    combo.setFocus()
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return _CANCELLED
    if editable and combo.currentText() != combo.itemText(combo.currentIndex()):
        return combo.currentText().strip()
    return combo.currentData() if combo.currentData() is not None else combo.currentText()


choose.CANCELLED = _CANCELLED
