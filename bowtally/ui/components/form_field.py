# -*- coding: utf-8 -*-
"""Form building blocks with inline validation.

FormField = input widget / optional hint / one-line error message.
Form groups fields in a QFormLayout (label left, widget right).
"""
import re
import datetime as dt
from typing import Callable

from PySide6.QtCore import QDate, QEvent, Qt, QTime, QTimer, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QAbstractSpinBox, QCalendarWidget, QCheckBox, QComboBox,
                               QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
                               QPlainTextEdit, QSizePolicy, QSpinBox, QTextEdit, QTimeEdit,
                               QVBoxLayout, QWidget)

from bowtally.ui import repolish, theme

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def email_validator(value) -> str | None:
    return None if not value or EMAIL_RE.match(value) else \
        "Bitte eine gültige E-Mail-Adresse eingeben (z. B. name@verein.de)"


DATE_FMT = "dd.MM.yyyy"


class DateField(QLineEdit):
    """Date in DD.MM.YYYY, typed directly into the pre-formatted mask __.__.____ or picked from
    the calendar (button at the right). With allow_empty the field may stay blank (no date)."""
    EMPTY = QDate(1900, 1, 1)
    dateChanged = Signal(QDate)

    def __init__(self, parent=None, allow_empty: bool = True):
        super().__init__(parent)
        self.allow_empty = allow_empty
        self.setInputMask("99.99.9999;_")
        self.setMinimumWidth(130)
        self._last = self.EMPTY                 # last complete, valid date (for dateChanged)
        self._popup = None
        self._cal_action = self.addAction(QIcon(), QLineEdit.ActionPosition.TrailingPosition)
        self._cal_action.setToolTip("Kalender öffnen")
        self._cal_action.triggered.connect(self.show_calendar)
        theme.notifier.changed.connect(self._update_icon)
        self._update_icon()
        self.textChanged.connect(self._on_text)
        self.editingFinished.connect(self._on_finished)

    def _update_icon(self):
        self._cal_action.setIcon(QIcon(theme.pixmap("calendar", theme.current()["text2"], 16)))

    # ---- value
    def _digits(self) -> str:
        return "".join(ch for ch in self.text() if ch.isdigit())

    def is_blank(self) -> bool:
        return not self._digits()

    def _parsed(self) -> QDate | None:
        """The typed date, or None when the input is incomplete or no real date."""
        d = QDate.fromString(self.text(), DATE_FMT)
        return d if d.isValid() and len(self._digits()) == 8 else None

    def input_error(self) -> str | None:
        if self.is_blank() or self._parsed() is not None:
            return None
        return "Bitte ein gültiges Datum im Format TT.MM.JJJJ eingeben"

    def date(self) -> QDate:
        d = self._parsed()
        if d is not None:
            return d
        return self._last if not self.allow_empty or not self.is_blank() else self.EMPTY

    def setDate(self, d) -> None:
        d = QDate(d) if d is not None and not isinstance(d, QDate) else d
        if d is None or not d.isValid() or (d == self.EMPTY and self.allow_empty):
            self.clear()
        else:
            self.setText(d.toString(DATE_FMT))

    def field_value(self) -> dt.date | None:
        d = self._parsed()
        return None if d is None or d == self.EMPTY else d.toPython()

    def set_field_value(self, value) -> None:
        self.setDate(QDate(value) if value else None)

    def _on_text(self, _text):
        d = self._parsed()
        if d is None and self.is_blank() and self.allow_empty:
            d = self.EMPTY
        if d is not None and d != self._last:
            self._last = d
            self.dateChanged.emit(d)

    def _on_finished(self):
        # a required date must not stay incomplete: fall back to the last valid date
        if not self.allow_empty and self._parsed() is None and self._last != self.EMPTY:
            self.setDate(self._last)

    # ---- direct input: clicking into an empty field starts at the first digit
    def _cursor_to_start_if_blank(self):
        if self.is_blank():
            self.setCursorPosition(0)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self._cursor_to_start_if_blank()

    def focusInEvent(self, event):
        super().focusInEvent(event)
        QTimer.singleShot(0, self._cursor_to_start_if_blank)

    # ---- calendar
    def show_calendar(self):
        if not self.isEnabled() or self.isReadOnly():
            return
        cal = QCalendarWidget()
        cal.setWindowFlags(Qt.WindowType.Popup)
        cal.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        cal.setGridVisible(False)
        cal.setFirstDayOfWeek(Qt.DayOfWeek.Monday)
        current = self._parsed()
        if current is not None:
            cal.setSelectedDate(current)
        else:
            today = QDate.currentDate()
            cal.setSelectedDate(today)
            cal.setCurrentPage(today.year(), today.month())
        cal.clicked.connect(lambda d: self._pick(cal, d))
        cal.activated.connect(lambda d: self._pick(cal, d))
        cal.adjustSize()
        pos = self.mapToGlobal(self.rect().bottomLeft())
        screen = self.screen().availableGeometry() if self.screen() else None
        if screen is not None:
            if pos.x() + cal.width() > screen.right():
                pos.setX(max(screen.left(), screen.right() - cal.width()))
            if pos.y() + cal.height() > screen.bottom():
                pos.setY(self.mapToGlobal(self.rect().topLeft()).y() - cal.height())
        cal.move(pos)
        cal.show()
        self._popup = cal

    def _pick(self, cal, d: QDate):
        self.setDate(d)
        cal.close()
        self._popup = None
        self.setFocus(Qt.FocusReason.PopupFocusReason)
        self.editingFinished.emit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F4 or (event.key() == Qt.Key.Key_Down
                                            and event.modifiers() & Qt.KeyboardModifier.AltModifier):
            self.show_calendar()
            return
        super().keyPressEvent(event)


class TimeField(QLineEdit):
    """Time in HH:MM, typed directly into the pre-formatted mask __:__.
    field_value() is "HH:mm" or None (blank)."""

    def __init__(self, parent=None, allow_empty: bool = True):
        super().__init__(parent)
        self.allow_empty = allow_empty
        self.setInputMask("99:99;_")
        self.setMinimumWidth(90)
        self._last = QTime()                    # last complete, valid time
        self.editingFinished.connect(self._on_finished)

    def _digits(self) -> str:
        return "".join(ch for ch in self.text() if ch.isdigit())

    def is_blank(self) -> bool:
        return not self._digits()

    def _parsed(self) -> QTime | None:
        t = QTime.fromString(self.text(), "HH:mm")
        return t if t.isValid() and len(self._digits()) == 4 else None

    def input_error(self) -> str | None:
        if self.is_blank() or self._parsed() is not None:
            return None
        return "Bitte eine gültige Uhrzeit im Format HH:MM eingeben"

    def time(self) -> QTime:
        t = self._parsed()
        return t if t is not None else self._last

    def setTime(self, t) -> None:
        if isinstance(t, str):
            t = QTime.fromString(t, "HH:mm")
        if t is None or not t.isValid():
            self.clear()
        else:
            self._last = t
            self.setText(t.toString("HH:mm"))

    def field_value(self) -> str | None:
        t = self._parsed()
        return None if t is None else t.toString("HH:mm")

    def set_field_value(self, value) -> None:
        self.setTime(str(value) if value else None)

    def _on_finished(self):
        t = self._parsed()
        if t is not None:
            self._last = t
        elif not self.allow_empty and self._last.isValid():
            self.setTime(self._last)            # a required time must not stay incomplete

    def _cursor_to_start_if_blank(self):
        if self.is_blank():
            self.setCursorPosition(0)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self._cursor_to_start_if_blank()

    def focusInEvent(self, event):
        super().focusInEvent(event)
        QTimer.singleShot(0, self._cursor_to_start_if_blank)


MIN_EURO_DIGITS = 2      # standard mask __,__ €; it grows while more euro digits are typed


def currency_mask(euro_digits: int) -> str:
    return "9" * euro_digits + ",99 €;_"


def format_currency(value: float) -> str:
    return f"{value:.2f} €".replace(".", ",")


class CurrencyField(QLineEdit):
    """Amount in euro: a blank field and the field while editing show the pre-formatted mask
    __,__ €. Typing a third (fourth) euro digit widens it to ___,__ € (____,__ €); "," or "."
    jumps to the cents. Otherwise the formatted amount is shown, e.g. "20,00 €".
    A blank field reads as None with allow_empty, else as 0."""
    valueChanged = Signal(float)

    def __init__(self, parent=None, allow_empty: bool = False, maximum: float = 9999.99):
        super().__init__(parent)
        self.allow_empty = allow_empty
        self.maximum = maximum
        self.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.setMinimumWidth(120)
        self._value: float | None = None
        self._max_digits = max(MIN_EURO_DIGITS, len(str(int(maximum))))
        self._slots = MIN_EURO_DIGITS          # euro digits of the current mask
        self._comma_typed = False
        self._show_formatted()
        self.textChanged.connect(self._on_text)

    # ---- parsing / formatting
    def _parse(self) -> float | None:
        raw = self.text().replace("€", "").replace("_", "").replace(" ", "").replace(".", "")
        if not raw.replace(",", ""):
            return None
        euros, _, cents = raw.partition(",")
        if not (euros or "0").isdigit() or (cents and not cents.isdigit()):
            return None
        return min(float(f"{euros or 0}.{(cents + '00')[:2]}"), self.maximum)

    def _show_formatted(self):
        """Not editing: a blank field shows the mask, an amount the formatted text."""
        self.blockSignals(True)
        if self._value is None:
            self._set_mask(MIN_EURO_DIGITS)
            self.clear()
        else:
            self.setInputMask("")
            self.setText(format_currency(self._value))
        self.blockSignals(False)

    def _show_mask(self):
        """Editing: the mask with the current amount (euros left-aligned, cents after ',')."""
        self.blockSignals(True)
        self._comma_typed = False
        if self._value is None:
            self._set_mask(MIN_EURO_DIGITS)
            self.clear()
        else:
            euros, cents = f"{self._value:.2f}".split(".")
            self._set_mask(len(euros))
            self.setText(f"{euros},{cents}")
            self._comma_typed = True            # an existing amount: digits stay where they are
        self.blockSignals(False)

    def _set_mask(self, euro_digits: int):
        self._slots = max(MIN_EURO_DIGITS, min(euro_digits, self._max_digits))
        self.setInputMask(currency_mask(self._slots))

    def _parts(self) -> tuple[str, str]:
        euros, _, cents = self.text().replace("€", "").replace(" ", "").partition(",")
        return euros.replace("_", ""), cents.replace("_", "")

    def keyPressEvent(self, event):
        if self.inputMask():
            text = event.text()
            if text in (",", "."):
                self._comma_typed = True
                self.setCursorPosition(self._slots + 1)
                return
            if text.isascii() and text.isdigit() and self._widen(text):
                return
        super().keyPressEvent(event)

    def _widen(self, digit: str) -> bool:
        """A further euro digit while the euro part is full: one more slot in front of ','."""
        euros, cents = self._parts()
        pos = self.cursorPosition()
        if (self._comma_typed or cents or len(euros) < self._slots
                or self._slots >= self._max_digits or pos not in (self._slots, self._slots + 1)):
            return False
        self._set_mask(self._slots + 1)
        self.setText(f"{euros}{digit},")
        self.setCursorPosition(self._slots + 1)     # behind ',': a further digit widens again
        return True

    def _on_text(self, _text):
        v = self._parse()
        if v != self._value:
            self._value = v
            self.valueChanged.emit(self.value())

    # ---- value API (compatible with QDoubleSpinBox where it is used)
    def value(self) -> float:
        return self._value or 0.0

    def setValue(self, value) -> None:
        v = None if value in (None, "") else float(value)
        if v is not None:
            v = max(0.0, min(v, self.maximum))
        changed = v != self._value
        self._value = v
        if self.hasFocus():
            self._show_mask()
        else:
            self._show_formatted()
        if changed:
            self.textChanged.emit(self.text())      # form change tracking
            self.valueChanged.emit(self.value())

    def field_value(self) -> float | None:
        if self._value is None:
            return None if self.allow_empty else 0.0
        return self._value

    def set_field_value(self, value) -> None:
        self.setValue(None if value in (None, "") else value)

    # ---- editing
    def focusInEvent(self, event):
        if not self.isReadOnly():
            self._show_mask()
        super().focusInEvent(event)
        QTimer.singleShot(0, self._cursor_to_start)

    def _cursor_to_start(self):
        if self.hasFocus() and self._value is None:
            self.setCursorPosition(0)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self._cursor_to_start()

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        if event.reason() != Qt.FocusReason.PopupFocusReason:
            self._show_formatted()


def read_value(w: QWidget):
    if hasattr(w, "field_value"):
        return w.field_value()
    if isinstance(w, QTimeEdit):
        t = w.time()
        if w.specialValueText() and t == w.minimumTime():
            return None
        return t.toString("HH:mm")
    if isinstance(w, QLineEdit):
        return w.text().strip()
    if isinstance(w, (QPlainTextEdit, QTextEdit)):
        return w.toPlainText().strip()
    if isinstance(w, QCheckBox):
        return w.isChecked()
    if isinstance(w, (QSpinBox, QDoubleSpinBox)):
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
    elif isinstance(w, QTimeEdit):
        w.setTime(QTime.fromString(str(value or ""), "HH:mm") if value else QTime(0, 0))
    elif isinstance(w, QLineEdit):
        w.setText("" if value is None else str(value))
    elif isinstance(w, (QPlainTextEdit, QTextEdit)):
        w.setPlainText(value or "")
    elif isinstance(w, QCheckBox):
        w.setChecked(bool(value))
    elif isinstance(w, QDoubleSpinBox):
        w.setValue(float(value or w.minimum()))
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
                 "timeChanged", "dateChanged"):
        if hasattr(w, name):
            return getattr(w, name)
    return None


def _apply_widget_policy(widget: QWidget) -> None:
    """Set size policies per layout rule: line edits expand; combos/pickers stay fixed."""
    if isinstance(widget, (DateField, TimeField, CurrencyField)):
        widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        widget.setMinimumWidth(160)
    elif isinstance(widget, (QLineEdit, QPlainTextEdit, QTextEdit)):
        vp = (QSizePolicy.Policy.Expanding if isinstance(widget, (QPlainTextEdit, QTextEdit))
              else QSizePolicy.Policy.Fixed)
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, vp)
    elif isinstance(widget, (QComboBox, QAbstractSpinBox)):
        widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        if isinstance(widget, QComboBox):
            widget.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        widget.setMinimumWidth(160)


class FormField(QWidget):
    """Right-hand column of a QFormLayout row: widget + optional hint + error label."""
    changed = Signal()

    def __init__(self, widget: QWidget, required: bool = False,
                 validator: Callable[[object], str | None] | None = None, hint: str = "",
                 required_message: str = "", label_text: str = "",
                 trailing: QWidget | None = None, parent=None):
        super().__init__(parent)
        self.widget = widget
        self.required, self.validator = required, validator
        self.required_message = required_message or f"{label_text} ist ein Pflichtfeld"
        self.error = QLabel(objectName="fieldError")
        self.error.setVisible(False)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(3)
        if trailing is None:
            lay.addWidget(widget)
        else:
            row = QHBoxLayout()
            row.setSpacing(8)
            row.addWidget(widget, 1)
            row.addWidget(trailing)
            lay.addLayout(row)
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
        input_error = getattr(self.widget, "input_error", None)
        message = input_error() if callable(input_error) else None
        if message:
            self.set_error(message)
            return False
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

    def __init__(self, label_width: int | None = None, combo_width: int | None = None,
                 parent=None):
        super().__init__(parent)
        self._label_width = label_width
        self._combo_width = combo_width
        self.fields: dict[str, FormField] = {}
        self._lay = QFormLayout(self)
        self._lay.setContentsMargins(0, 0, 0, 0)
        self._lay.setSpacing(10)
        self._lay.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._lay.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

    def add(self, key: str, label: str, widget: QWidget, required: bool = False,
            short: bool = False, **kwargs) -> FormField:
        _apply_widget_policy(widget)
        if self._combo_width is not None and (short or isinstance(widget, (QComboBox, QAbstractSpinBox, DateField,
                                                          TimeField, CurrencyField))):
            widget.setFixedWidth(self._combo_width)
        field = FormField(widget, required=required, label_text=label, **kwargs)
        h_pol = widget.sizePolicy().horizontalPolicy()
        if h_pol in (QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding):
            field.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        field.changed.connect(self.changed)
        self.fields[key] = field
        if isinstance(widget, QCheckBox):
            self._lay.addRow("", field)
        else:
            lbl_text = f"{label} *" if required else label
            lbl = QLabel(lbl_text, objectName="fieldLabel")
            lbl.setBuddy(widget)
            if self._label_width is not None:
                lbl.setFixedWidth(self._label_width)
            self._lay.addRow(lbl, field)
        return field

    def add_widget(self, widget: QWidget) -> None:
        self._lay.addRow(widget)

    def add_note(self, widget: QWidget) -> None:
        """A line below the fields, aligned with the field column (not with the labels)."""
        self._lay.addRow("", widget)

    def set_labels_on_top(self) -> None:
        """Label above the field, field in full width."""
        self._lay.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        self._lay.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

    def set_row_visible(self, key: str, visible: bool) -> None:
        """Show or hide a field together with its label."""
        self._lay.setRowVisible(self.fields[key], visible)

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
