# -*- coding: utf-8 -*-
"""Side drawer for create/edit forms: slides in from the right and takes space from the
content (no overlay). One instance per view, reused for 'new' and 'edit'."""
from PySide6.QtCore import QEasingCurve, QEvent, QPropertyAnimation, QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QPlainTextEdit,
                               QScrollArea, QSizePolicy, QTextEdit, QToolButton, QVBoxLayout,
                               QWidget)

from bowtally.ui import button, mark_dirty, theme
from bowtally.ui.components.confirm_dialog import ConfirmDialog
from bowtally.ui.components.form_field import Form

WIDTH = 480
ANIM_MS = 300


class SideDrawer(QFrame):
    saveRequested = Signal()
    closed = Signal()

    def __init__(self, form: Form, parent=None):
        super().__init__(parent)
        self.setObjectName("drawer")
        self.form = form
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        self.setMaximumWidth(0)
        self.hide()
        self._open = False
        self._baseline = None
        self._read_only = False

        self.title = QLabel(objectName="drawerTitle")
        self.close_btn = QToolButton(objectName="iconButton")
        self.close_btn.setToolTip("Schließen (Esc)")
        self.close_btn.clicked.connect(self.request_close)
        head = QHBoxLayout()
        head.setContentsMargins(24, 20, 16, 12)
        head.addWidget(self.title, 1)
        head.addWidget(self.close_btn)

        body = QWidget()
        b_lay = QVBoxLayout(body)
        b_lay.setContentsMargins(24, 4, 24, 16)
        b_lay.addWidget(form)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setWidget(body)

        self.cancel_btn = button("Abbrechen", self.request_close,
                                 tooltip="Änderungen verwerfen und schließen (Esc)")
        self.save_btn = button("Speichern", self.saveRequested.emit, "primary",
                               "Speichern (Enter oder Strg+S)")
        footer = QWidget(objectName="drawerFooter")
        footer.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        f_lay = QHBoxLayout(footer)
        f_lay.setContentsMargins(24, 12, 24, 14)
        f_lay.addStretch()
        f_lay.addWidget(self.cancel_btn)
        f_lay.addWidget(self.save_btn)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addLayout(head)
        lay.addWidget(self.scroll, 1)
        lay.addWidget(footer)

        form.changed.connect(self._update_dirty)
        self._anim = QPropertyAnimation(self, b"maximumWidth", self)
        self._anim.setDuration(ANIM_MS)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.finished.connect(self._anim_done)
        theme.notifier.changed.connect(self._update_icon)
        self._update_icon()

    def sizeHint(self) -> QSize:
        return QSize(WIDTH, super().sizeHint().height())

    def _update_icon(self):
        self.close_btn.setIcon(QIcon(theme.pixmap("x", theme.current()["text2"], 18)))

    # ------------------------------------------------------------ open / close
    def is_open(self) -> bool:
        return self._open

    def open(self, title: str, read_only: bool = False, read_only_hint: str = "") -> None:
        """Call after the form was filled (or reset). Takes the dirty-check baseline."""
        self.title.setText(title)
        self._read_only = read_only
        self.form.set_read_only(read_only)
        self.save_btn.setEnabled(not read_only)
        self.save_btn.setToolTip(read_only_hint if read_only else "Speichern (Enter oder Strg+S)")
        self.cancel_btn.setText("Abbrechen")
        self._baseline = self.form.snapshot()
        self._update_dirty()
        self.scroll.verticalScrollBar().setValue(0)
        if not self._open:
            self._open = True
            self.show()
            self._animate(WIDTH)
            QApplication.instance().installEventFilter(self)
        self.form.focus_first()

    def _update_dirty(self):
        mark_dirty(self.save_btn, self.is_dirty())

    def is_dirty(self) -> bool:
        return not self._read_only and self._baseline is not None \
            and self.form.snapshot() != self._baseline

    def request_close(self) -> bool:
        """Close with dirty check. Returns False if the user kept editing."""
        if not self._open:
            return True
        if self.is_dirty() and not ConfirmDialog.ask(
                self, "Änderungen verwerfen?",
                "Die Eingaben in diesem Formular wurden noch nicht gespeichert.",
                "Verwerfen"):
            return False
        self.close_now()
        return True

    def close_now(self) -> None:
        if not self._open:
            return
        self._open = False
        QApplication.instance().removeEventFilter(self)
        self._animate(0)
        self.closed.emit()

    def mark_saved(self) -> None:
        """After a successful save: no dirty prompt, then close."""
        self._baseline = self.form.snapshot()
        self._update_dirty()
        self.close_now()

    def _animate(self, end: int):
        self._anim.stop()
        self._anim.setStartValue(self.maximumWidth())
        self._anim.setEndValue(end)
        self._anim.start()

    def _anim_done(self):
        if not self._open:
            self.hide()

    # ------------------------------------------------------------ keyboard / mouse
    def keyPressEvent(self, event):
        key = event.key()
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            focus = QApplication.focusWidget()
            if not isinstance(focus, (QTextEdit, QPlainTextEdit)) and not self._read_only:
                self.saveRequested.emit()
                return
        elif key == Qt.Key.Key_Escape:
            self.request_close()
            return
        super().keyPressEvent(event)

    def eventFilter(self, obj, event):
        """Click outside the drawer (same window, not a popup or dialog) closes it."""
        if event.type() == QEvent.Type.MouseButtonPress and isinstance(obj, QWidget) \
                and obj.isWindow() is False and obj.window() is self.window() \
                and obj is not self and not self.isAncestorOf(obj):
            if not self.request_close():
                return True     # user keeps editing: the click must not trigger anything
        return False
