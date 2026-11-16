# -*- coding: utf-8 -*-
"""Volunteer management: global master data (no tournament) and per-tournament assignments."""
from PySide6.QtCore import QSettings, Qt, QTime
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QDialog, QGroupBox, QHBoxLayout,
                               QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QPlainTextEdit, QScrollArea, QTabWidget, QTableWidget,
                               QTableWidgetItem, QTimeEdit, QVBoxLayout, QWidget)

from bowtally.io.importer import HELPER_IMPORT_FIELDS
from bowtally.services import helper_service as hs
from bowtally.services.settings_service import KEY_EMAIL_TPL_HELPER
from bowtally.ui import busy, button, show_error
from bowtally.ui.utils.mailto import open_mailto, tournament_ctx
from bowtally.ui.components.action_bar import Action
from bowtally.ui.components.confirm_dialog import ConfirmDialog
from bowtally.ui.components.data_table import Cell, ROW_HEIGHT
from bowtally.ui.components.empty_state import EmptyState
from bowtally.ui.components.form_field import email_validator
from bowtally.ui.components.search_bar import SearchBar
from bowtally.ui.components.toast import Toast
from bowtally.ui.context import context
from bowtally.ui.dialogs.export_helper import export_button
from bowtally.ui.dialogs.import_dialog import run_import
from bowtally.ui.dialogs.record_dialog import RecordDialog
from bowtally.ui.views import ListView

GLOBAL_HEADERS = ["Name", "Telefon", "E-Mail", "Notizen", "Status"]
TOURNAMENT_HEADERS = ["Name", "Aufgabe", "Von", "Bis", "Bestätigt", "Status", "Telefon", "E-Mail"]
GLOBAL_EXPORT_HEADERS = ["Nachname", "Vorname", "Telefon", "E-Mail", "Notizen"]


class _HelperPicker(QDialog):
    """Pick one or more helpers from the global master data to assign to a tournament."""

    def __init__(self, already_assigned_ids: set[int], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Helfer aus Stammdatei zuweisen")
        self.resize(500, 480)
        self.search = SearchBar("Name suchen …")
        self.list = QListWidget()
        helpers = hs.list_helpers(include_inactive=True)
        for h in helpers:
            text = f"{h.last_name}, {h.first_name}"
            details = " · ".join(x for x in (h.phone, h.email) if x)
            item = QListWidgetItem(f"{text}   {details}" if details else text)
            item.setData(Qt.ItemDataRole.UserRole, h.id)
            item.setData(Qt.ItemDataRole.UserRole + 1,
                         f"{text} {h.email or ''} {h.phone or ''}".lower())
            if h.active:
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
            else:
                item.setFlags(Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                item.setToolTip("Helfer ist inaktiv.")
                item.setForeground(item.foreground().color().darker(160))
            self.list.addItem(item)
        self.search.searchChanged.connect(self._filter)
        self.list.itemActivated.connect(self._toggle)
        self.ok = button("Zuweisen (0)", self.accept, "primary",
                         "Ausgewählte Helfer dem Turnier zuweisen")
        self.list.itemChanged.connect(self._update_ok)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(button("Abbrechen", self.reject, tooltip="Nichts zuweisen"))
        row.addWidget(self.ok)
        lay = QVBoxLayout(self)
        lay.addWidget(self.search)
        lay.addWidget(self.list, 1)
        lay.addLayout(row)
        self._update_ok()

    def _toggle(self, item):
        item.setCheckState(Qt.CheckState.Unchecked if item.checkState()
                           == Qt.CheckState.Checked else Qt.CheckState.Checked)

    def _filter(self, term: str):
        term = term.lower()
        for i in range(self.list.count()):
            item = self.list.item(i)
            item.setHidden(bool(term) and term not in item.data(Qt.ItemDataRole.UserRole + 1))

    def _update_ok(self, *_):
        n = len(self.selected_ids())
        self.ok.setText(f"Zuweisen ({n})")
        self.ok.setEnabled(n > 0)

    def selected_ids(self) -> list[int]:
        return [self.list.item(i).data(Qt.ItemDataRole.UserRole)
                for i in range(self.list.count())
                if self.list.item(i).checkState() == Qt.CheckState.Checked]


class HelperDialog(RecordDialog):
    """Create / edit a helper (global) or a tournament assignment (tournament mode)."""
    _default_size = (698, 584)

    def __init__(self, record=None, tournament_id=None, parent=None):
        self._record = record
        self._tournament_id = tournament_id
        self._is_tournament = tournament_id is not None
        if record is None:
            title = "Neuer Helfer"
        elif not self._is_tournament:
            title = f"{record.first_name} {record.last_name}"
        else:
            title = f"{record.helper.first_name} {record.helper.last_name}"
        super().__init__(title, parent=parent)
        if self._record is not None and not self._is_tournament:
            main_lay = self.layout()
            for i in range(main_lay.count()):
                w = main_lay.itemAt(i).widget() if main_lay.itemAt(i) else None
                if isinstance(w, QScrollArea):
                    main_lay.removeWidget(w)
                    tabs = QTabWidget()
                    tabs.addTab(w, "Stammdaten")
                    tabs.addTab(self._build_history(self._record.id), "Turnierbeteiligung")
                    main_lay.insertWidget(i, tabs, 1)
                    break
        values: dict = {"confirmed": False, "active": True}
        if record is not None:
            if not self._is_tournament:
                values = {"first_name": record.first_name, "last_name": record.last_name,
                          "phone": record.phone, "email": record.email, "notes": record.notes,
                          "active": record.active}
            else:
                values = {"first_name": record.helper.first_name,
                          "last_name": record.helper.last_name,
                          "phone": record.helper.phone, "email": record.helper.email,
                          "notes": record.helper.notes, "task": record.task,
                          "time_from": record.time_from, "time_to": record.time_to,
                          "confirmed": record.confirmed}
        self.form.set_values(values)
        self._baseline = self.form.snapshot()
        self.saved_id: int | None = None
        self.saved_name: str = ""

    def _setup_form(self):
        notes = QPlainTextEdit()
        notes.setMinimumHeight(70)
        self.form.add("first_name", "Vorname", QLineEdit(), required=True)
        self.form.add("last_name", "Nachname", QLineEdit(), required=True)
        self.form.add("phone", "Telefon", QLineEdit())
        self.form.add("email", "E-Mail", QLineEdit(), validator=email_validator)
        self.form.add("notes", "Notizen", notes)
        if not self._is_tournament:
            self.form.add("active", "Status", QCheckBox("Aktiv"))
        if self._is_tournament:
            def _te():
                w = QTimeEdit()
                w.setDisplayFormat("HH:mm")
                w.setSpecialValueText("–")
                w.setTime(QTime(0, 0))
                return w
            self.form.add("task", "Aufgabe", QLineEdit(),
                          hint="z. B. Parcours-Aufbau, Einschreibung, Ergebnisse")
            self.form.add("time_from", "Zeit von", _te())
            self.form.add("time_to", "Zeit bis", _te())
            self.form.add("confirmed", "Bestätigt", QCheckBox("Bestätigung versendet"))

    def _build_history(self, helper_id: int) -> QWidget:
        history = hs.get_helper_history(helper_id)
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        if not history:
            lay.addWidget(QLabel("Noch bei keinem Turnier eingesetzt.",
                                 objectName="pageSubtitle"))
        else:
            t = QTableWidget(len(history), 5)
            t.setHorizontalHeaderLabels(["Turniername", "Datum", "Aufgabe",
                                         "Einsatzzeit", "Bestätigt"])
            t.verticalHeader().hide()
            t.verticalHeader().setDefaultSectionSize(ROW_HEIGHT)
            t.setShowGrid(False)
            t.setAlternatingRowColors(True)
            t.setWordWrap(False)
            t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            t.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
            h = t.horizontalHeader()
            h.setHighlightSections(False)
            h.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            h.setStretchLastSection(True)
            h.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            for r, row in enumerate(history):
                date_str = f"{row['date']:%d.%m.%Y}" if row.get('date') else "–"
                tf, tt = row.get('time_from') or "", row.get('time_to') or ""
                time_str = f"{tf}–{tt}" if tf or tt else "–"
                t.setItem(r, 0, QTableWidgetItem(row.get('name') or "–"))
                t.setItem(r, 1, QTableWidgetItem(date_str))
                t.setItem(r, 2, QTableWidgetItem(row.get('task') or "–"))
                t.setItem(r, 3, QTableWidgetItem(time_str))
                t.setItem(r, 4, QTableWidgetItem("Ja" if row.get('confirmed') else "Nein"))
            lay.addWidget(t)
        return w

    def _do_save(self) -> bool:
        values = self.form.values()
        try:
            with busy():
                if self._tournament_id is None:
                    if self._record is None:
                        result = hs.create_helper(values)
                    else:
                        result = hs.update_helper(self._record.id, values)
                    self.saved_id = result.id
                    self.saved_name = f"{result.first_name} {result.last_name}"
                else:
                    if self._record is None:
                        result = hs.create_and_assign(self._tournament_id, values)
                    else:
                        result = hs.update_assignment(self._record.id, values)
                    self.saved_id = result.id
                    self.saved_name = (f"{result.helper.first_name} "
                                       f"{result.helper.last_name}")
        except Exception as exc:
            show_error(self, exc, "Helfer konnte nicht gespeichert werden")
            return False
        return True


class HelpersView(ListView):
    def __init__(self, tournament_mode: bool = False, parent=None):
        # Sidebar page = global master data; tab in an open tournament = assignments
        self._tournament_mode = tournament_mode
        empty = EmptyState("users", "Keine Helfer",
                           "Lege neue Helfer an oder importiere eine Helferliste.",
                           "Neuer Helfer")
        super().__init__("Helfer", TOURNAMENT_HEADERS, empty,
                         search_placeholder="Name oder Aufgabe …")
        empty.actionTriggered.connect(self.new_item)

        self._btn_from_master = button("Aus Stammdatei", self._pick_from_master,
                                       tooltip="Helfer aus globaler Stammdatei zuweisen")
        self._btn_new = button("Neuer Helfer", self.new_item, "primary",
                               "Neuen Helfer anlegen (Strg+N)")
        self.header.add(self._btn_from_master)
        self.header.add(self._btn_new)

        footer = QWidget()
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(0, 4, 0, 0)
        self._show_inactive = QCheckBox("Inaktive Helfer anzeigen")
        _s = QSettings("BowTally", "BowTally")
        self._show_inactive.setChecked(_s.value("helpers/show_inactive", False, type=bool))
        self._show_inactive.toggled.connect(self.refresh)
        self._show_inactive.toggled.connect(
            lambda v: QSettings("BowTally", "BowTally").setValue("helpers/show_inactive", v))
        fl.addWidget(self._show_inactive)
        fl.addStretch()
        self._btn_export = export_button(self, "helfer", self._export_sheets,
                                         lambda: len(self.table.visible_ids())
                                         if self.table.is_filtered() else None)
        self._btn_import = button("Importieren", self._import,
                                  tooltip="Helfer aus CSV, Excel oder OpenDocument importieren")
        self._btn_print = button("Helferliste drucken", self._print_list,
                                 tooltip="Helferliste als PDF erstellen")
        fl.addWidget(self._btn_export)
        fl.addWidget(self._btn_import)
        fl.addWidget(self._btn_print)
        self.main_layout.insertWidget(2, footer)
        self.table.activated.connect(self.edit_item)
        self._rows: dict[int, object] = {}

    @property
    def _tid(self):
        return context.tournament_id if self._tournament_mode else None

    def set_tournament(self, _t):
        self.refresh()

    # ---------------------------------------------------------------- data
    def refresh(self):
        tid = self._tid
        has_tournament = tid is not None

        self._btn_from_master.setVisible(has_tournament)
        self._btn_new.setVisible(True)
        self._btn_export.setVisible(not has_tournament)
        self._btn_import.setVisible(not has_tournament)
        self._btn_print.setVisible(has_tournament)

        if not has_tournament:
            self._rows = {}
            self.table.set_headers(GLOBAL_HEADERS)
            show_inactive = self._show_inactive.isChecked()
            with busy():
                helpers = hs.list_helpers(include_inactive=True)
            if not show_inactive:
                helpers = [h for h in helpers if h.active]
            self._rows = {h.id: h for h in helpers}
            self.table.set_rows([[
                f"{h.last_name}, {h.first_name}",
                h.phone or "",
                h.email or "",
                h.notes or "",
                Cell(h.active, chip=("Aktiv", "success") if h.active else ("Inaktiv", "muted")),
            ] for h in helpers], [h.id for h in helpers])
            self.header.set_subtitle(f"{len(helpers)} Helfer in Stammdatei")
        else:
            self._rows = {}
            self.table.set_headers(TOURNAMENT_HEADERS)
            with busy():
                rows = hs.list_tournament_helpers(tid)
            if not self._show_inactive.isChecked():
                rows = [r for r in rows if r.helper.active]
            self._rows = {r.id: r for r in rows}
            self.table.set_rows([[
                f"{r.helper.last_name}, {r.helper.first_name}",
                r.task or "",
                r.time_from or "",
                r.time_to or "",
                Cell(r.confirmed, chip=("Ja", "success") if r.confirmed else ("Nein", "muted")),
                Cell(r.helper.active,
                     chip=("Aktiv", "success") if r.helper.active else ("Inaktiv", "muted")),
                r.helper.phone or "",
                r.helper.email or "",
            ] for r in rows], [r.id for r in rows])
            confirmed = sum(1 for r in rows if r.confirmed)
            self.header.set_subtitle(f"{len(rows)} Helfer | {confirmed} bestätigt")
        self.on_selection(self.table.selected_ids())

    # ---------------------------------------------------------------- selection
    def on_selection(self, ids: list):
        n = len(ids)
        if n == 0:
            self.action_bar.set_actions("", [])
            return
        if self._tid is None:
            actions = [Action("Bearbeiten", self.edit_item, tooltip="Helfer bearbeiten")]
            if n == 1:
                h = self._rows.get(ids[0])
                if h:
                    label = "Als inaktiv markieren" if h.active else "Wieder aktivieren"
                    _hid, _na = ids[0], not h.active
                    actions.append(Action(label, lambda: self._toggle_global_active(_hid, _na)))
            actions.append(Action(f"{n} Helfer löschen" if n > 1 else "Löschen",
                                  self.delete_selected, "danger"))
            self.action_bar.set_actions(self.selection_info(n, "Helfer", "Helfer"), actions)
        else:
            actions = [Action("Bearbeiten", self.edit_item, tooltip="Helfereinsatz bearbeiten")]
            actions.append(Action(f"{n} Helfer entfernen" if n > 1 else "Entfernen",
                                  self.delete_selected, "danger"))
            self.action_bar.set_actions(self.selection_info(n, "Helfer", "Helfer"), actions)

    def context_entries(self, row_id):
        if self._tid is None:
            h = self._rows.get(row_id)
            if h is None:
                return []
            _na = not h.active
            return [
                ("Bearbeiten", self.edit_item),
                ("Als inaktiv markieren" if h.active else "Wieder aktivieren",
                 lambda: self._toggle_global_active(row_id, _na)),
                None,
                ("Löschen", self.delete_selected),
            ]
        else:
            th = self._rows.get(row_id)
            if th is None:
                return []
            entries = [("Bearbeiten", self.edit_item)]
            if th.helper.email:
                entries.append(("Bestätigung senden", lambda: self._mailto(row_id)))
            _nc, _na = not th.confirmed, not th.helper.active
            entries += [
                ("Als bestätigt markieren" if not th.confirmed else "Bestätigung zurücksetzen",
                 lambda: self._toggle_confirmed(row_id, _nc)),
                ("Als inaktiv markieren" if th.helper.active else "Wieder aktivieren",
                 lambda: self._set_helper_active(row_id, _na)),
                None,
                ("Entfernen", self.delete_selected),
            ]
            return entries

    # ---------------------------------------------------------------- new / edit
    def new_item(self):
        dlg = HelperDialog(tournament_id=self._tid, parent=self)
        if dlg.exec() and dlg.saved_id:
            Toast.show(self, f"{dlg.saved_name} gespeichert", Toast.SUCCESS)
            self.refresh()
            self.table.select_ids([dlg.saved_id])

    def edit_item(self, *_):
        sel_ids = self.table.selected_ids()
        if not sel_ids:
            return
        record = self._rows.get(sel_ids[0])
        if record is None:
            return
        dlg = HelperDialog(record=record, tournament_id=self._tid, parent=self)
        if dlg.exec() and dlg.saved_id:
            Toast.show(self, f"{dlg.saved_name} gespeichert", Toast.SUCCESS)
            self.refresh()
            self.table.select_ids([dlg.saved_id])

    # ---------------------------------------------------------------- actions
    def delete_selected(self):
        ids = self.table.selected_ids()
        if not ids:
            return
        if self._tid is not None:
            names = ", ".join(f"{self._rows[i].helper.first_name} {self._rows[i].helper.last_name}"
                              for i in ids if i in self._rows)
            if not ConfirmDialog.ask(self, "Helfer entfernen?",
                                     f"{names}\n\nDer Einsatz wird aus diesem Turnier entfernt.",
                                     "Entfernen", destructive=True):
                return
            try:
                with busy():
                    for aid in ids:
                        hs.remove_assignment(aid)
            except Exception as exc:
                show_error(self, exc, "Helfer konnte nicht entfernt werden")
                return
            Toast.show(self, f"{len(ids)} Helfer entfernt", Toast.SUCCESS)
        else:
            names = ", ".join(f"{self._rows[i].first_name} {self._rows[i].last_name}"
                              for i in ids if i in self._rows)
            if not ConfirmDialog.ask(self, "Helfer löschen?",
                                     f"{names}\n\nHelfer wird endgültig gelöscht.",
                                     "Löschen", destructive=True):
                return
            with busy():
                blocked = [i for i in ids if hs.helper_has_assignments(i)]
                for i in ids:
                    if i not in blocked:
                        hs.delete_helper(i)
            deleted = len(ids) - len(blocked)
            if blocked and ConfirmDialog.ask(
                    self, "Turnierdaten vorhanden",
                    f"{len(blocked)} Helfer wurden bereits bei Turnieren eingesetzt und können "
                    "nicht gelöscht werden. Stattdessen als inaktiv markieren?",
                    "Deaktivieren", destructive=False):
                for i in blocked:
                    hs.set_active(i, False)
                Toast.show(self, f"{len(blocked)} Helfer deaktiviert", Toast.INFO)
            if deleted:
                Toast.show(self, f"{deleted} Helfer gelöscht", Toast.SUCCESS)
        self.refresh()

    def _toggle_global_active(self, helper_id: int, active: bool):
        try:
            hs.set_active(helper_id, active)
        except Exception as exc:
            show_error(self, exc)
            return
        self.refresh()

    def _toggle_confirmed(self, assignment_id: int, confirmed: bool):
        try:
            hs.set_confirmed(assignment_id, confirmed)
        except Exception as exc:
            show_error(self, exc)
            return
        self.refresh()

    def _set_helper_active(self, assignment_id: int, active: bool):
        th = self._rows.get(assignment_id)
        if th is None:
            return
        try:
            hs.set_active(th.helper_id, active)
        except Exception as exc:
            show_error(self, exc)
            return
        self.refresh()

    def _pick_from_master(self):
        tid = self._tid
        if tid is None:
            return
        dlg = _HelperPicker(set(), self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        ids = dlg.selected_ids()
        if not ids:
            return
        try:
            with busy():
                added = [hs.assign_existing(tid, hid) for hid in ids]
        except Exception as exc:
            show_error(self, exc, "Helfer konnten nicht zugewiesen werden")
            return
        Toast.show(self, f"{len(added)} Helfer zugewiesen", Toast.SUCCESS)
        self.refresh()
        self.table.select_ids([a.id for a in added])

    def _print_list(self):
        tid = self._tid
        if tid is None:
            return
        from bowtally.reports.helper_list import build_helper_list
        from bowtally.ui.dialogs.export_helper import open_path
        try:
            with busy():
                path = build_helper_list(tid)
        except Exception as exc:
            show_error(self, exc, "Helferliste konnte nicht erstellt werden")
            return
        Toast.show(self, "Helferliste erstellt", Toast.SUCCESS,
                   ("Öffnen", lambda: open_path(self, path)))

    def _mailto(self, assignment_id: int):
        th = self._rows.get(assignment_id)
        if th is None:
            return
        t = context.tournament()
        if t is None:
            return
        open_mailto(KEY_EMAIL_TPL_HELPER, th.helper.email, {
            "name": f"{th.helper.first_name} {th.helper.last_name}",
            "turniername": t.name,
            "datum": f"{t.date:%d.%m.%Y}",
            "aufgabe": th.task or "",
            "von": th.time_from or "",
            "bis": th.time_to or "",
            **tournament_ctx(t),
        }, self)

    # ---------------------------------------------------------------- import / export
    def _import(self):
        res = run_import(self, HELPER_IMPORT_FIELDS, "Helfer importieren")
        if res is None:
            return
        records, strategy = res
        try:
            with busy():
                r = hs.import_helpers(records, strategy)
        except Exception as exc:
            show_error(self, exc, "Import fehlgeschlagen")
            return
        Toast.show(self, f"Import abgeschlossen: {r['created']} neu, {r['updated']} "
                         f"aktualisiert, {r['skipped']} übersprungen", Toast.SUCCESS)
        self.refresh()

    def _export_sheets(self, filtered: bool):
        ids = self.table.visible_ids() if filtered else list(self._rows)
        rows = []
        for i in ids:
            h = self._rows.get(i)
            if h:
                rows.append([h.last_name, h.first_name, h.phone, h.email, h.notes])
        return [("Helfer", GLOBAL_EXPORT_HEADERS, rows)]
