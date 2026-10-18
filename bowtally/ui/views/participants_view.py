# -*- coding: utf-8 -*-
"""Participant management of one tournament: picker, inline editing, bulk actions, import."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel,
                               QListWidget, QListWidgetItem, QVBoxLayout, QWidget)

from bowtally.io.importer import PARTICIPANT_IMPORT_FIELDS
from bowtally.services import master_data_service as md
from bowtally.services import tournament_service as ts
from bowtally.ui import busy, button, show_error
from bowtally.ui.components.action_bar import Action, ActionBar
from bowtally.ui.components.confirm_dialog import ConfirmDialog, choose
from bowtally.ui.components.data_table import Cell, ComboDelegate, DataTable
from bowtally.ui.components.empty_state import EmptyState
from bowtally.ui.components.search_bar import SearchBar
from bowtally.ui.components.toast import Toast
from bowtally.ui.dialogs.import_dialog import run_import
from bowtally.ui.views import menu

HEADERS = ["St.-Nr.", "Name", "Verein", "Bogenklasse", "Startgruppe", "Startzeit"]
COL_NO, COL_CLASS, COL_GROUP, COL_TIME = 0, 3, 4, 5
ALL_GROUPS = "__all__"
CLOSED_HINT = "Das Turnier ist abgeschlossen, Änderungen sind gesperrt."


class ArcherPicker(QDialog):
    """Search + check boxes; archers already in the tournament are greyed out."""

    def __init__(self, assigned_ids: set[int], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Schützen zuweisen")
        self.resize(560, 600)
        self.search = SearchBar("Name, Verein oder Mitgliedsnummer …")
        self.list = QListWidget()
        self.archers = {a.id: a for a in md.list_archers()}
        for a in self.archers.values():
            text = f"{a.last_name}, {a.first_name}"
            details = " · ".join(x for x in (a.club, a.default_bow_class.name
                                              if a.default_bow_class else None) if x)
            item = QListWidgetItem(f"{text}   {details}" if details else text)
            item.setData(Qt.ItemDataRole.UserRole, a.id)
            item.setData(Qt.ItemDataRole.UserRole + 1,
                         f"{text} {a.club or ''} {a.member_number or ''}".lower())
            if a.id in assigned_ids:
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                item.setToolTip("Bereits diesem Turnier zugewiesen")
            else:
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
            self.list.addItem(item)
        self.list.itemChanged.connect(self._update_count)
        self.list.itemActivated.connect(self._toggle)
        self.search.searchChanged.connect(self._filter)
        self.ok = button("Hinzufügen (0)", self.accept, "primary",
                         "Ausgewählte Schützen dem Turnier zuweisen")
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(button("Abbrechen", self.reject, tooltip="Nichts zuweisen"))
        row.addWidget(self.ok)
        hint = QLabel("Anklicken zum Auswählen. Grau = bereits zugewiesen.",
                      objectName="pageSubtitle")
        lay = QVBoxLayout(self)
        lay.addWidget(self.search)
        lay.addWidget(self.list, 1)
        lay.addWidget(hint)
        lay.addLayout(row)
        self._update_count()

    def _toggle(self, item):
        if item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
            item.setCheckState(Qt.CheckState.Unchecked if item.checkState()
                               == Qt.CheckState.Checked else Qt.CheckState.Checked)

    def _filter(self, term: str):
        term = term.lower()
        for i in range(self.list.count()):
            item = self.list.item(i)
            item.setHidden(bool(term) and term not in item.data(Qt.ItemDataRole.UserRole + 1))

    def selected_ids(self) -> list[int]:
        return [self.list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.list.count())
                if self.list.item(i).checkState() == Qt.CheckState.Checked]

    def _update_count(self, *_):
        n = len(self.selected_ids())
        self.ok.setText(f"Hinzufügen ({n})")
        self.ok.setEnabled(n > 0)


class ClassAssignDialog(QDialog):
    """Asks for a bow class for archers whose default class is not part of the tournament."""

    def __init__(self, archers: list, classes: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bogenklasse zuordnen")
        info = QLabel("Für diese Schützen ist die Standardklasse im Turnier nicht aktiv. "
                      "Bitte eine Klasse wählen:")
        info.setWordWrap(True)
        form = QFormLayout()
        self.combos = {}
        for a in archers:
            cb = QComboBox()
            for bc in classes:
                cb.addItem(bc.name, bc.id)
            self.combos[a.id] = cb
            form.addRow(f"{a.first_name} {a.last_name}", cb)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(button("Abbrechen", self.reject, tooltip="Nicht zuweisen"))
        row.addWidget(button("Speichern", self.accept, "primary", "Klassen übernehmen"))
        lay = QVBoxLayout(self)
        lay.addWidget(info)
        lay.addLayout(form)
        lay.addLayout(row)

    def choices(self) -> dict[int, int]:
        return {aid: cb.currentData() for aid, cb in self.combos.items()}


class ParticipantsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tournament = None
        self._parts = {}
        self.search = SearchBar("Teilnehmer suchen …")
        self.search.searchChanged.connect(lambda _t: self._apply_filter())
        self.group_filter = QComboBox()
        self.group_filter.setToolTip("Nach Startgruppe filtern")
        self.group_filter.currentIndexChanged.connect(lambda _i: self._apply_filter())
        self.btn_add = button("Schütze zuweisen", self.pick_archers, "primary",
                              "Schützen aus den Stammdaten zuweisen (Strg+N)")
        self.btn_import = button("Importieren", self._import,
                                 tooltip="Teilnehmerliste aus CSV, Excel oder OpenDocument")
        self.btn_renumber = button("Startnummern neu vergeben", self._renumber,
                                   tooltip="Nummern 1..n nach Klasse und Name, Gruppen reihum")
        bar = QHBoxLayout()
        bar.addWidget(self.search)
        bar.addWidget(self.group_filter)
        bar.addStretch()
        bar.addWidget(self.btn_renumber)
        bar.addWidget(self.btn_import)
        bar.addWidget(self.btn_add)

        empty = EmptyState("users", "Noch keine Teilnehmer",
                           "Weise Schützen aus den Stammdaten zu oder importiere eine "
                           "Teilnehmerliste.", "Schütze zuweisen")
        empty.actionTriggered.connect(self.pick_archers)
        self.table = DataTable(HEADERS, empty, multi_select=True)
        self.table.set_delegate(COL_CLASS, ComboDelegate(self._class_options, parent=self))
        self.table.set_delegate(COL_GROUP, ComboDelegate(self._group_options, editable=True,
                                                         parent=self))
        self.table.cellEdited.connect(self._on_cell_edited)
        self.table.selectionChanged.connect(self._on_selection)
        self.table.contextMenuRequested.connect(self._context_menu)
        self.action_bar = ActionBar()
        hint = QLabel("Doppelklick auf Startnummer, Bogenklasse, Startgruppe oder Startzeit "
                      "bearbeitet direkt in der Tabelle. Tab springt zur nächsten Zelle.",
                      objectName="pageSubtitle")
        hint.setWordWrap(True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.addLayout(bar)
        lay.addWidget(self.table, 1)
        lay.addWidget(self.action_bar)
        lay.addWidget(hint)

    # ------------------------------------------------------------ data
    def set_tournament(self, tournament):
        self.tournament = t = tournament
        editable = t.status != "closed"
        for b in (self.btn_add, self.btn_import, self.btn_renumber):
            b.setEnabled(editable)
            b.setToolTip(b.toolTip() if editable else CLOSED_HINT)
        parts = sorted(t.participants, key=lambda p: (p.start_number or 10**9,
                                                      p.archer.last_name))
        self._parts = {p.id: p for p in parts}
        self.table.set_rows([[Cell(p.start_number, editable=editable),
                              f"{p.archer.last_name}, {p.archer.first_name}", p.archer.club,
                              Cell(p.bow_class.name if p.bow_class else "",
                                   data=p.bow_class_id, editable=editable),
                              Cell(p.start_group, editable=editable),
                              Cell(p.start_time, editable=editable)] for p in parts],
                            [p.id for p in parts])
        current = self.group_filter.currentData()
        self.group_filter.blockSignals(True)
        self.group_filter.clear()
        self.group_filter.addItem("Alle Startgruppen", ALL_GROUPS)
        groups = sorted(set(ts.split_groups(t.start_groups))
                        | {p.start_group for p in parts if p.start_group})
        for g in groups:
            self.group_filter.addItem(f"Gruppe {g}", g)
        self.group_filter.setCurrentIndex(max(0, self.group_filter.findData(current)))
        self.group_filter.setVisible(bool(groups))
        self.group_filter.blockSignals(False)
        self._apply_filter()
        self._on_selection(self.table.selected_ids())

    def _reload(self):
        self.set_tournament(ts.get_tournament(self.tournament.id))

    def _apply_filter(self):
        self.table.apply_filter(self.search.term())
        group = self.group_filter.currentData()
        if group not in (None, ALL_GROUPS):
            for r in range(self.table.table.rowCount()):
                item = self.table.table.item(r, COL_GROUP)
                if item is not None and item.text() != group:
                    self.table.table.setRowHidden(r, True)

    def _class_options(self):
        return [(bc.name, bc.id) for bc in self.tournament.bow_classes]

    def _group_options(self):
        return [("", "")] + [(g, g) for g in ts.split_groups(self.tournament.start_groups)]

    # ------------------------------------------------------------ inline editing
    def _on_cell_edited(self, pid, column, value):
        key = {COL_NO: "start_number", COL_CLASS: "bow_class_id", COL_GROUP: "start_group",
               COL_TIME: "start_time"}.get(column)
        if key is None:
            return
        if key == "start_number":
            text = str(value).strip()
            if text and not text.isdigit():
                Toast.show(self, f"Startnummer '{text}' ist keine Zahl", Toast.WARNING)
                self._reload()
                return
            value = int(text) if text else None
        try:
            ts.update_participant(pid, {key: value})
        except Exception as exc:
            show_error(self, exc)
        self._reload()

    # ------------------------------------------------------------ selection / bulk
    def _selected(self):
        return [self._parts[i] for i in self.table.selected_ids() if i in self._parts]

    def _on_selection(self, ids):
        n = len(ids)
        locked = self.tournament is not None and self.tournament.status == "closed"
        tip = CLOSED_HINT if locked else ""
        actions = [] if not n else [
            Action("Klasse ändern", self.change_class, enabled=not locked,
                   tooltip=tip or "Bogenklasse für die Auswahl setzen"),
            Action("Gruppe ändern", self.change_group, enabled=not locked,
                   tooltip=tip or "Startgruppe für die Auswahl setzen"),
            Action("Entfernen", self.remove_selected, "danger", enabled=not locked,
                   tooltip=tip or "Aus dem Turnier entfernen (mit Rückfrage)")]
        self.action_bar.set_actions(
            "1 Teilnehmer ausgewählt" if n == 1 else f"{n} Teilnehmer ausgewählt", actions)

    def _context_menu(self, _pid, pos):
        locked = self.tournament.status == "closed"
        menu(self, [("Klasse ändern …", self.change_class, not locked, CLOSED_HINT),
                    ("Gruppe ändern …", self.change_group, not locked, CLOSED_HINT),
                    None,
                    ("Entfernen", self.remove_selected, not locked, CLOSED_HINT)]).exec(pos)

    def change_class(self):
        sel = self._selected()
        if not sel:
            return
        cid = choose(self, "Klasse ändern", f"Bogenklasse für {len(sel)} Teilnehmer:",
                     self._class_options(), sel[0].bow_class_id)
        if cid is choose.CANCELLED:
            return
        with busy():
            for p in sel:
                ts.update_participant(p.id, {"bow_class_id": cid})
        Toast.show(self, f"Klasse für {len(sel)} Teilnehmer geändert", Toast.SUCCESS)
        self._reload()

    def change_group(self):
        sel = self._selected()
        if not sel:
            return
        group = choose(self, "Gruppe ändern", f"Startgruppe für {len(sel)} Teilnehmer:",
                       self._group_options()[1:] or [("", "")], sel[0].start_group,
                       editable=True)
        if group is choose.CANCELLED:
            return
        with busy():
            for p in sel:
                ts.update_participant(p.id, {"start_group": group or None})
        Toast.show(self, f"Startgruppe für {len(sel)} Teilnehmer geändert", Toast.SUCCESS)
        self._reload()

    def remove_selected(self):
        sel = self._selected()
        if not sel:
            return
        with_scores = [p for p in sel if ts.participant_has_scores(p.id)]
        text = (f"{sel[0].archer.first_name} {sel[0].archer.last_name} wird aus dem Turnier "
                "entfernt." if len(sel) == 1 else f"{len(sel)} Teilnehmer werden aus dem Turnier "
                "entfernt.")
        if with_scores:
            text += f"\n\nAchtung: Für {len(with_scores)} davon sind bereits Ergebnisse " \
                    "erfasst. Diese werden gelöscht."
        if not ConfirmDialog.ask(self, "Teilnehmer entfernen?", text, "Entfernen"):
            return
        with busy():
            for p in sel:
                ts.remove_participant(p.id)
        Toast.show(self, f"{len(sel)} Teilnehmer entfernt", Toast.SUCCESS)
        self._reload()

    # ------------------------------------------------------------ add / import
    def pick_archers(self):
        if self.tournament is None or self.tournament.status == "closed":
            return
        t = self.tournament
        picker = ArcherPicker({p.archer_id for p in t.participants}, self)
        if not picker.exec() or not picker.selected_ids():
            return
        ids = picker.selected_ids()
        active = {bc.id for bc in t.bow_classes}
        unresolved = [picker.archers[i] for i in ids
                      if picker.archers[i].default_bow_class_id not in active]
        choices = {}
        if unresolved:
            dlg = ClassAssignDialog(unresolved, t.bow_classes, self)
            if not dlg.exec():
                return
            choices = dlg.choices()
        with busy():
            added = ts.add_participants(t.id, ids)
            if choices:
                by_archer = {p.archer_id: p.id for p in ts.get_tournament(t.id).participants}
                for aid, cid in choices.items():
                    ts.update_participant(by_archer[aid], {"bow_class_id": cid})
        Toast.show(self, f"{added} Teilnehmer zugewiesen", Toast.SUCCESS)
        self._reload()

    def _renumber(self):
        if ConfirmDialog.ask(self, "Startnummern neu vergeben?",
                             "Alle Startnummern werden neu von 1 an vergeben (sortiert nach "
                             "Klasse und Name), Startgruppen werden reihum verteilt.",
                             "Neu vergeben", destructive=False):
            ts.assign_start_numbers(self.tournament.id)
            Toast.show(self, "Startnummern neu vergeben", Toast.SUCCESS)
            self._reload()

    def _import(self):
        res = run_import(self, PARTICIPANT_IMPORT_FIELDS, "Teilnehmerliste importieren")
        if res is None:
            return
        records, strategy = res
        try:
            with busy():
                r = ts.import_participants(self.tournament.id, records, strategy)
        except Exception as exc:
            show_error(self, exc, "Import fehlgeschlagen")
            return
        Toast.show(self, f"{r['added']} Teilnehmer hinzugefügt ({r['created']} Schützen neu "
                         f"angelegt, {r['updated']} aktualisiert)", Toast.SUCCESS)
        self._reload()

    # global shortcuts
    def shortcut_new(self):
        self.pick_archers()

    def shortcut_find(self):
        self.search.setFocus()
        self.search.selectAll()
