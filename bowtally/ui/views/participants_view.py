# -*- coding: utf-8 -*-
"""Participant management of one tournament."""
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
                               QLabel, QLineEdit, QMessageBox, QSpinBox, QVBoxLayout, QWidget)

from bowtally.io.importer import PARTICIPANT_IMPORT_FIELDS
from bowtally.services import master_data_service as md
from bowtally.services import tournament_service as ts
from bowtally.ui import button, confirm, show_error
from bowtally.ui.dialogs.import_dialog import run_import
from bowtally.ui.widgets.sortable_table import SortableTable

HEADERS = ["St.-Nr.", "Name", "Verein", "Bogenklasse", "Startgruppe", "Startzeit"]


class AddArchersDialog(QDialog):
    """Pick archers from master data (search + multi selection)."""

    def __init__(self, exclude_ids: set[int], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Schützen hinzufügen")
        self.resize(720, 520)
        archers = [a for a in md.list_archers() if a.id not in exclude_ids]
        self.table = SortableTable(["Nachname", "Vorname", "Verein", "Mitgliedsnr.",
                                    "Standardklasse"], multi_select=True)
        self.table.set_rows([[a.last_name, a.first_name, a.club, a.member_number,
                              a.default_bow_class.name if a.default_bow_class else None]
                             for a in archers], [a.id for a in archers])
        self.table.activated.connect(lambda _id: self.accept())
        hint = QLabel("Mehrfachauswahl mit Strg/Umschalt.")
        hint.setProperty("secondary", True)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                   | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Hinzufügen")
        buttons.button(QDialogButtonBox.StandardButton.Ok).setProperty("primary", True)
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Abbrechen")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addWidget(self.table, 1)
        lay.addWidget(hint)
        lay.addWidget(buttons)


class ParticipantDialog(QDialog):
    def __init__(self, tournament, participant, parent=None):
        super().__init__(parent)
        self.participant_id = participant.id
        self.setWindowTitle(f"Teilnehmer: {participant.archer.first_name} "
                            f"{participant.archer.last_name}")
        self.bow_class = QComboBox()
        for bc in tournament.bow_classes:
            self.bow_class.addItem(bc.name, bc.id)
        self.bow_class.setCurrentIndex(max(0, self.bow_class.findData(participant.bow_class_id)))
        self.start_number = QSpinBox()
        self.start_number.setRange(0, 99999)
        self.start_number.setSpecialValueText("-")
        self.start_number.setValue(participant.start_number or 0)
        self.start_group = QComboBox()
        self.start_group.setEditable(True)
        self.start_group.addItems([""] + ts.split_groups(tournament.start_groups))
        self.start_group.setCurrentText(participant.start_group or "")
        self.start_time = QLineEdit(participant.start_time or "")
        self.start_time.setPlaceholderText("z. B. 09:30")
        form = QFormLayout()
        form.addRow("Bogenklasse", self.bow_class)
        form.addRow("Startnummer", self.start_number)
        form.addRow("Startgruppe", self.start_group)
        form.addRow("Startzeit", self.start_time)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save
                                   | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Speichern")
        buttons.button(QDialogButtonBox.StandardButton.Save).setProperty("primary", True)
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Abbrechen")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(buttons)

    def _save(self):
        try:
            ts.update_participant(self.participant_id, {
                "bow_class_id": self.bow_class.currentData(),
                "start_number": self.start_number.value() or None,
                "start_group": self.start_group.currentText().strip(),
                "start_time": self.start_time.text().strip()})
        except Exception as exc:
            show_error(self, exc, "Teilnehmer konnte nicht gespeichert werden")
            return
        self.accept()


class ParticipantsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tournament = None
        self.table = SortableTable(HEADERS)
        self.table.activated.connect(lambda _id: self._edit())
        self.edit_buttons = [button("Schützen hinzufügen ...", self._add, "primary"),
                             button("Bearbeiten", self._edit),
                             button("Entfernen", self._remove, "danger"),
                             button("Startnummern neu vergeben", self._renumber),
                             button("Import ...", self._import)]
        bar = QHBoxLayout()
        for b in self.edit_buttons:
            bar.addWidget(b)
        bar.insertStretch(3)
        self.count = QLabel()
        self.count.setProperty("secondary", True)
        lay = QVBoxLayout(self)
        lay.addLayout(bar)
        lay.addWidget(self.table, 1)
        lay.addWidget(self.count)

    def set_tournament(self, tournament):
        self.tournament = tournament
        editable = tournament.status != "closed"
        for b in self.edit_buttons:
            b.setEnabled(editable)
        parts = sorted(tournament.participants, key=lambda p: (p.start_number or 10**9))
        self._parts = {p.id: p for p in parts}
        self.table.set_rows([[p.start_number, f"{p.archer.last_name}, {p.archer.first_name}",
                              p.archer.club, p.bow_class.name if p.bow_class else None,
                              p.start_group, p.start_time] for p in parts],
                            [p.id for p in parts])
        self.count.setText(f"{len(parts)} Teilnehmer")

    def _reload(self):
        self.set_tournament(ts.get_tournament(self.tournament.id))

    def _add(self):
        dlg = AddArchersDialog({p.archer_id for p in self.tournament.participants}, self)
        if dlg.exec() and dlg.table.selected_ids():
            ts.add_participants(self.tournament.id, dlg.table.selected_ids())
            self._reload()

    def _edit(self):
        p = self._parts.get(self.table.selected_id())
        if p is None or self.tournament.status == "closed":
            return
        if ParticipantDialog(self.tournament, p, self).exec():
            self._reload()

    def _remove(self):
        p = self._parts.get(self.table.selected_id())
        if p is None:
            return
        text = f"{p.archer.first_name} {p.archer.last_name} aus dem Turnier entfernen?"
        if ts.participant_has_scores(p.id):
            text += "\n\nACHTUNG: Bereits erfasste Ergebnisse werden gelöscht!"
        if confirm(self, text):
            ts.remove_participant(p.id)
            self._reload()

    def _renumber(self):
        if confirm(self, "Alle Startnummern neu vergeben (nach Klasse und Name)?"):
            ts.assign_start_numbers(self.tournament.id)
            self._reload()

    def _import(self):
        res = run_import(self, PARTICIPANT_IMPORT_FIELDS, "Teilnehmerliste importieren")
        if res is None:
            return
        records, strategy = res
        try:
            r = ts.import_participants(self.tournament.id, records, strategy)
        except Exception as exc:
            show_error(self, exc, "Import fehlgeschlagen")
            return
        QMessageBox.information(
            self, "Import", f"Teilnehmer hinzugefügt: {r['added']}\n"
                            f"Schützen neu angelegt: {r['created']}\n"
                            f"Schützen aktualisiert: {r['updated']}\n"
                            f"Vorhandene Schützen übernommen: {r['skipped']}")
        self._reload()
