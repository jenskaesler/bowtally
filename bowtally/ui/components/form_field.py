# -*- coding: utf-8 -*-
"""Form building blocks with inline validation.

FormField = label (+ red asterisk) / input widget / one-line error message.
Validation runs on focus-out and on save; an error disappears as soon as the value changes.
Form groups fields, collects values and offers a snapshot for dirty checks.
"""
import re
from datetime import date
from typing import Callable

from PySide6.QtCore import QDate, QEvent, Qt, QTimer, Signal
from PySide6.QtWidgets import (QAbstractSpinBox, QCheckBox, QComboBox, QDateEdit, QHBoxLayout,
                               QLabel, QLineEdit, QPlainTextEdit, QSizePolicy, QSpinBox,
                               QTextEdit, QVBoxLayout, QWidget)

from bowtally.ui import repolish

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def email_validator(value) -> str | None:
    return None if not value or EMAIL_RE.match(value) else \
        "Bitte eine gültige E-Mail-Adresse eingeben (z. B. name@verein.de)"


class DateField(QDateEdit):
    """Optional date in DD.MM.YYYY; the minimum date stands for 'no date'."""
    EMPTY = QDate(1900, 1, 1)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDisplayFormat("dd.MM.yyyy")
        self.setCalendarPopup(True)
        self.setMinimumDate(self.EMPTY)
        self.setSpecialValueText("–")
        self.setDate(self.EMPTY)
        self.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)

    def field_value(self) -> date | None:
        return None if self.date() == self.EMPTY else self.date().toPython()

    def set_field_value(self, value) -> None:
        self.setDate(QDate(value) if value else self.EMPTY)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if self.date() == self.EMPTY:   # empty: open the calendar near today, not in 1900
            today = QDate.currentDate()
            QTimer.singleShot(0, lambda: self.calendarWidget().setCurrentPage(
                today.year(), today.month()))


def read_value(w: QWidget):
    if hasattr(w, "field_value"):
        return w.field_value()
    if isinstance(w, QLineEdit):
        return w.text().strip()
    if isinstance(w, (QPlainTextEdit, QTextEdit)):
        return w.toPlainText().strip()
    if isinstance(w, QCheckBox):
        return w.isChecked()
    if isinstance(w, QSpinBox):
        return w.value()
    if isinstance(w, QComboBox):
        if w.isEditable():
            return w.currentText().strip()
        # combos with item data return the data (None allowed, e.g. "(keine)"), else the text
        if any(w.itemData(i) is not None for i in range(w.count())):
            return w.currentData()
        return w.currentText()
    raise TypeError(f"Unsupported widget {type(w).__name__}")


def write_value(w: QWidget, value) -> None:
    if hasattr(w, "set_field_value"):
        w.set_field_value(value)
    elif isinstance(w, QLineEdit):
        w.setText("" if value is None else str(value))
    elif isinstance(w, (QPlainTextEdit, QTextEdit)):
        w.setPlainText(value or "")
    elif isinstance(w, QCheckBox):
        w.setChecked(bool(value))
    elif isinstance(w, QSpinBox):
        w.setValue(int(value or w.minimum()))
    elif isinstance(w, QComboBox):
        idx = w.findData(value) if value is not None else -1
        if idx < 0 and value is not None:
            idx = w.findText(str(value))
        if w.isEditable() and idx < 0:
            w.setEditText("" if value is None else str(value))
        else:
            w.setCurrentIndex(max(idx, 0))


def _change_signal(w: QWidget):
    for name in ("changed", "textChanged", "currentTextChanged", "toggled", "valueChanged",
                 "dateChanged"):
        if hasattr(w, name):
            return getattr(w, name)
    return None


class FormField(QWidget):
    changed = Signal()

    def __init__(self, label: str, widget: QWidget, required: bool = False,
                 validator: Callable[[object], str | None] | None = None, hint: str = "",
                 required_message: str = "", parent=None):
        super().__init__(parent)
        self.label_text, self.widget = label, widget
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.required, self.validator = required, validator
        self.required_message = required_message or f"{label} ist ein Pflichtfeld"
        head = QHBoxLayout()
        head.setSpacing(2)
        lbl = QLabel(label, objectName="fieldLabel")
        lbl.setBuddy(widget)
        head.addWidget(lbl)
        if required:
            head.addWidget(QLabel("*", objectName="fieldRequired"))
        head.addStretch()
        self.error = QLabel(objectName="fieldError")
        self.error.setVisible(False)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        if not isinstance(widget, QCheckBox):    # a check box carries its own text
            lay.addLayout(head)
        lay.addWidget(widget)
        if hint:
            lay.addWidget(QLabel(hint, objectName="fieldHint", wordWrap=True))
        lay.addWidget(self.error)
        signal = _change_signal(widget)
        if signal is not None:
            signal.connect(self._on_change)
        widget.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.FocusOut and obj is self.widget \
                and event.reason() != Qt.FocusReason.PopupFocusReason:
            self.validate()
        return False

    def _on_change(self, *_):
        if self.error.isVisible():
            self.clear_error()
        self.changed.emit()

    def value(self):
        return read_value(self.widget)

    def set_value(self, value) -> None:
        write_value(self.widget, value)
        self.clear_error()

    def validate(self) -> bool:
        value = self.value()
        if self.required and value in (None, "", []):
            self.set_error(self.required_message)
            return False
        message = self.validator(value) if self.validator else None
        if message:
            self.set_error(message)
            return False
        self.clear_error()
        return True

    def set_error(self, message: str) -> None:
        self.error.setText(message)
        self.error.setVisible(True)
        self.widget.setProperty("invalid", True)
        repolish(self.widget)

    def clear_error(self) -> None:
        self.error.setVisible(False)
        self.widget.setProperty("invalid", False)
        repolish(self.widget)

    def set_read_only(self, read_only: bool) -> None:
        w = self.widget
        if isinstance(w, (QLineEdit, QPlainTextEdit, QTextEdit)):
            w.setReadOnly(read_only)
        else:
            w.setEnabled(not read_only)


class Form(QWidget):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.fields: dict[str, FormField] = {}
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(0, 0, 0, 0)
        self._lay.setSpacing(14)
        self._lay.addStretch()

    def add(self, key: str, label: str, widget: QWidget, **kwargs) -> FormField:
        field = FormField(label, widget, **kwargs)
        field.changed.connect(self.changed)
        self.fields[key] = field
        self._lay.insertWidget(self._lay.count() - 1, field)
        return field

    def add_widget(self, widget: QWidget) -> None:
        """Non-field content (hints, section titles)."""
        self._lay.insertWidget(self._lay.count() - 1, widget)

    def values(self) -> dict:
        return {k: f.value() for k, f in self.fields.items()}

    def set_values(self, values: dict) -> None:
        for k, f in self.fields.items():
            f.set_value(values.get(k))

    def snapshot(self) -> tuple:
        return tuple(repr(f.value()) for f in self.fields.values())

    def validate(self) -> bool:
        """Validate all fields; focus the first invalid one."""
        first = None
        for f in self.fields.values():
            if not f.validate() and first is None:
                first = f
        if first is not None:
            first.widget.setFocus()
            return False
        return True

    def set_error(self, key: str, message: str) -> None:
        self.fields[key].set_error(message)
        self.fields[key].widget.setFocus()

    def set_read_only(self, read_only: bool) -> None:
        for f in self.fields.values():
            f.set_read_only(read_only)

    def focus_first(self) -> None:
        for f in self.fields.values():
            if f.widget.isEnabled():
                f.widget.setFocus()
                if isinstance(f.widget, QLineEdit):
                    f.widget.selectAll()
                return
