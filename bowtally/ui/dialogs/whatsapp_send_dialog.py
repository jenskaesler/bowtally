# -*- coding: utf-8 -*-
"""Sequential WhatsApp sending to several recipients.

Every wa.me call replaces the chat opened before in WhatsApp Desktop / Web, so recipients are
worked through one after another, controlled by the user. "Bestätigt" is only ever set by the
user ("Als gesendet markieren"): opening a chat does not mean the message was sent.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QHBoxLayout, QHeaderView, QLabel,
                               QTableWidget, QTableWidgetItem, QVBoxLayout)

from bowtally.ui import button, restore_geom, save_geom
from bowtally.ui.utils.whatsapp import normalize_phone, open_whatsapp

OPEN, OPENED, CONFIRMED, SKIPPED = "Offen", "Geöffnet", "Bestätigt", "Übersprungen"
NO_PHONE = "Übersprungen – keine gültige Nummer"


class WhatsAppSendDialog(QDialog):
    def __init__(self, template_key: str, recipients: list[tuple[str, str | None, dict]],
                 title: str = "Nachricht per WhatsApp senden", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(620, 460)
        restore_geom(self, "whatsapp_send")
        self.finished.connect(lambda: save_geom(self, "whatsapp_send"))
        self.template_key = template_key
        self.recipients = recipients
        self.status = [OPEN if normalize_phone(phone) else NO_PHONE
                       for _n, phone, _c in recipients]

        info = QLabel("Öffne den Chat, sende die Nachricht in WhatsApp und markiere sie hier "
                      "als gesendet. WhatsApp zeigt immer nur einen Chat – deshalb geht es "
                      "Empfänger für Empfänger weiter.", objectName="pageSubtitle")
        info.setWordWrap(True)
        self.table = QTableWidget(len(recipients), 3)
        self.table.setHorizontalHeaderLabels(["Name", "Telefon", "Status"])
        self.table.verticalHeader().hide()
        self.table.setShowGrid(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        h.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        for row, (name, phone, _ctx) in enumerate(recipients):
            self.table.setItem(row, 0, QTableWidgetItem(name))
            self.table.setItem(row, 1, QTableWidgetItem(phone or "–"))
            self.table.setItem(row, 2, QTableWidgetItem(self.status[row]))
        self.table.itemSelectionChanged.connect(self._update)
        self.progress = QLabel(objectName="pageSubtitle")

        self.btn_open = button("WhatsApp öffnen", self.open_current, "primary",
                               "Chat mit dem markierten Empfänger öffnen")
        self.btn_sent = button("Als gesendet markieren", self.mark_sent,
                               tooltip="Bestätigen, dass du die Nachricht in WhatsApp gesendet hast")
        self.btn_next = button("Nächster Empfänger", self.next_recipient,
                               tooltip="Zum nächsten offenen Empfänger; ein nicht geöffneter "
                                       "Empfänger wird als übersprungen markiert")
        row = QHBoxLayout()
        row.addWidget(self.progress, 1)
        row.addWidget(self.btn_open)
        row.addWidget(self.btn_sent)
        row.addWidget(self.btn_next)
        row.addWidget(button("Schließen", self.accept))
        lay = QVBoxLayout(self)
        lay.addWidget(info)
        lay.addWidget(self.table, 1)
        lay.addLayout(row)
        first = self._next_open(-1)
        self.table.selectRow(first if first is not None else 0)
        self._update()

    # ------------------------------------------------------------ state
    def current(self) -> int | None:
        rows = self.table.selectionModel().selectedRows()
        return rows[0].row() if rows else None

    def _sendable(self, row: int | None) -> bool:
        return row is not None and self.status[row] != NO_PHONE

    def _next_open(self, after: int) -> int | None:
        for row in range(after + 1, len(self.status)):
            if self.status[row] in (OPEN, OPENED):
                return row
        return None

    def _set_status(self, row: int, status: str):
        self.status[row] = status
        self.table.item(row, 2).setText(status)
        self._update()

    def done_count(self) -> int:
        return sum(s != OPEN for s in self.status)

    def _update(self):
        row = self.current()
        sendable = self._sendable(row)
        self.btn_open.setEnabled(sendable)
        self.btn_sent.setEnabled(sendable and self.status[row] != CONFIRMED)
        self.btn_next.setEnabled(row is not None and self._next_open(row) is not None)
        confirmed = sum(s == CONFIRMED for s in self.status)
        self.progress.setText(f"{self.done_count()} von {len(self.status)} bearbeitet · "
                              f"{confirmed} als gesendet markiert")

    # ------------------------------------------------------------ actions
    def open_current(self):
        row = self.current()
        if not self._sendable(row):
            return
        _name, phone, ctx = self.recipients[row]
        if open_whatsapp(self.template_key, phone, ctx, self) and self.status[row] == OPEN:
            self._set_status(row, OPENED)

    def mark_sent(self):
        row = self.current()
        if self._sendable(row):
            self._set_status(row, CONFIRMED)

    def next_recipient(self):
        row = self.current()
        if row is None:
            return
        if self.status[row] == OPEN:            # moved on without opening the chat
            self._set_status(row, SKIPPED)
        nxt = self._next_open(row)
        if nxt is not None:
            self.table.selectRow(nxt)
