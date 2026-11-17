# -*- coding: utf-8 -*-
"""Archer master data: search, modal CRUD, import / export, soft and hard delete."""
from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QCompleter, QHBoxLayout,
                               QHeaderView, QLabel, QLineEdit, QPlainTextEdit, QScrollArea,
                               QTabWidget, QTableWidget, QTableWidgetItem, QVBoxLayout,
                               QWidget)

from bowtally.io.importer import ARCHER_IMPORT_FIELDS
from bowtally.services import master_data_service as md
from bowtally.ui import busy, button, show_error
from bowtally.ui.components.action_bar import Action
from bowtally.ui.components.confirm_dialog import ConfirmDialog, choose
from bowtally.ui.components.data_table import Cell, ROW_HEIGHT
from bowtally.ui.components.empty_state import EmptyState
from bowtally.ui.components.files_panel import FilesPanel
from bowtally.ui.components.form_field import DateField, Form, email_validator
from bowtally.ui.components.toast import Toast
from bowtally.ui.dialogs.export_helper import export_button
from bowtally.ui.dialogs.import_dialog import run_import
from bowtally.ui.dialogs.record_dialog import RecordDialog
from bowtally.ui.views import ListView

HEADERS = ["Vorname", "Nachname", "Verein", "Klasse", "Mitgliedsnummer", "Status"]
EXPORT_HEADERS = ["Nachname", "Vorname", "Geburtsdatum", "Verein", "Mitgliedsnummer",
                  "Bogenklasse", "E-Mail", "Telefon", "Aktiv"]


class ArcherDialog(RecordDialog):
    _default_size = (1060, 716)

    def __init__(self, record=None, parent=None):
        self._record = record
        super().__init__(
            "Neuer Schütze" if record is None else
            f"{record.first_name} {record.last_name}", parent=parent)
        main_lay = self.layout()
        for i in range(main_lay.count()):
            w = main_lay.itemAt(i).widget() if main_lay.itemAt(i) else None
            if isinstance(w, QScrollArea):
                main_lay.removeWidget(w)
                tabs = QTabWidget()
                tabs.addTab(w, "Stammdaten")
                if record is not None:
                    tabs.addTab(self._build_history(record.id), "Turnierhistorie")
                tabs.addTab(self._build_notes(), "Notizen")
                tabs.addTab(FilesPanel(
                    None if record is None else record.id, "Schützen", md.list_archer_files,
                    md.add_archer_file, md.remove_archer_file, md.archer_file_path), "Dokumente")
                main_lay.insertWidget(i, tabs, 1)
                break
        values: dict = {"active": True}
        if record:
            values = {k: getattr(record, k) for k in (*self.form.fields, "notes")}
        self.form.set_values(values)
        self.notes_form.set_values(values)
        self._baseline = self._snapshot()
        self.saved_id: int | None = None
        self.saved_name: str = ""

    def _setup_form(self):
        bow_class = QComboBox()
        bow_class.addItem("(keine)", None)
        for bc in md.list_bow_classes():
            bow_class.addItem(bc.name, bc.id)
        club = QLineEdit()
        archers = md.list_archers(include_inactive=True)
        club.setCompleter(QCompleter(sorted({a.club for a in archers if a.club})))
        self.form.add("first_name", "Vorname", QLineEdit(), required=True)
        self.form.add("last_name", "Nachname", QLineEdit(), required=True)
        self.form.add("birth_date", "Geburtsdatum", DateField(),
                      hint="Format TT.MM.JJJJ, optional")
        self.form.add("club", "Verein", club)
        self.form.add("member_number", "Mitgliedsnummer", QLineEdit(), short=True)
        self.form.add("default_bow_class_id", "Standardklasse", bow_class)
        email_field = QLineEdit()
        self.form.add("email", "E-Mail", email_field, validator=email_validator)
        self.form.add("phone", "Telefon", QLineEdit(), short=True)
        self.form.add("active", "Aktiv", QCheckBox("Aktiv (in Auswahllisten sichtbar)"))
        notify_cb = QCheckBox("Bei neuen Turnieren per E-Mail benachrichtigen")
        self.form.add("notify_new_tournament", "Benachrichtigung", notify_cb)
        results_cb = QCheckBox("Ergebnisversand per E-Mail")
        self.form.add("notify_results", "Ergebnisversand", results_cb)
        # disable notify checkboxes when no e-mail address is set
        def _update_notify(*_):
            has_email = bool(email_field.text().strip())
            for cb in (notify_cb, results_cb):
                if not has_email:
                    cb.setChecked(False)
                cb.setEnabled(has_email)
                cb.setToolTip("" if has_email else
                              "Nur verfügbar wenn eine E-Mail-Adresse hinterlegt ist.")
        email_field.textChanged.connect(_update_notify)
        _update_notify()

    def _build_notes(self) -> QWidget:
        self.notes_form = Form()
        self.notes_form.set_labels_on_top()
        notes = QPlainTextEdit()
        notes.setMinimumHeight(110)
        self.notes_form.add("notes", "Notizen", notes)
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 8, 0, 0)
        lay.addWidget(self.notes_form)
        lay.addStretch()
        return page

    def _snapshot(self) -> tuple:
        return self.form.snapshot() + self.notes_form.snapshot()

    def _is_dirty(self) -> bool:
        return self._snapshot() != self._baseline

    def _build_history(self, archer_id: int) -> QWidget:
        history = md.get_archer_history(archer_id)
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        if not history:
            lay.addWidget(QLabel("Noch an keinem Turnier teilgenommen.",
                                 objectName="pageSubtitle"))
        else:
            t = QTableWidget(len(history), 7)
            t.setHorizontalHeaderLabels(["Turniername", "Datum", "Bogenklasse",
                                         "Anmeldestatus", "Zahlungsstatus", "Rang", "Punkte"])
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
                t.setItem(r, 0, QTableWidgetItem(row.get('name') or "–"))
                t.setItem(r, 1, QTableWidgetItem(date_str))
                t.setItem(r, 2, QTableWidgetItem(row.get('bow_class') or "–"))
                t.setItem(r, 3, QTableWidgetItem(row.get('registration_status') or "–"))
                t.setItem(r, 4, QTableWidgetItem(row.get('payment_status') or "–"))
                rank = row.get('rank')
                t.setItem(r, 5, QTableWidgetItem(f"{rank}." if rank else "–"))
                total = row.get('total')
                t.setItem(r, 6, QTableWidgetItem(str(total) if total is not None else "–"))
            lay.addWidget(t)
        return w

    def _do_save(self) -> bool:
        try:
            with busy():
                archer = md.save_archer({**self.form.values(), **self.notes_form.values()},
                                        self._record.id if self._record else None)
        except Exception as exc:
            show_error(self, exc, "Schütze konnte nicht gespeichert werden")
            return False
        self.saved_id = archer.id
        self.saved_name = f"{archer.first_name} {archer.last_name}"
        return True


class ArchersView(ListView):
    def __init__(self, parent=None):
        empty = EmptyState("users", "Noch keine Schützen",
                           "Lege den ersten Schützen an oder importiere eine Mitgliederliste.",
                           "Neuer Schütze")
        super().__init__("Schützen", HEADERS, empty,
                         search_placeholder="Name, Verein oder Mitgliedsnummer …",
                         multi_select=True)
        empty.actionTriggered.connect(self.new_item)
        self._show_inactive = QCheckBox("Inaktive Schützen anzeigen")
        _s = QSettings("BowTally", "BowTally")
        self._show_inactive.setChecked(_s.value("archers/show_inactive", False, type=bool))
        self._show_inactive.toggled.connect(self.refresh)
        self._show_inactive.toggled.connect(
            lambda v: QSettings("BowTally", "BowTally").setValue("archers/show_inactive", v))
        self.header.add(
            button("Neuer Schütze", self.new_item, "primary", "Neuen Schützen anlegen (Strg+N)"))
        _footer = QWidget()
        _fl = QHBoxLayout(_footer)
        _fl.setContentsMargins(0, 4, 0, 0)
        _fl.addWidget(self._show_inactive)
        _fl.addStretch()
        _fl.addWidget(export_button(self, "schuetzen", self._export_sheets,
                                    lambda: len(self.table.visible_ids())
                                    if self.table.is_filtered() else None))
        _fl.addWidget(button("Importieren", self._import,
                             tooltip="Schützen aus CSV, Excel oder OpenDocument importieren"))
        self.main_layout.insertWidget(2, _footer)
        self.table.activated.connect(self.edit_item)
        self._archers = {}

    # ------------------------------------------------------------ data
    def refresh(self):
        with busy():
            archers = md.list_archers(include_inactive=True)
        self._archers = {a.id: a for a in archers}
        visible = archers if self._show_inactive.isChecked() else [a for a in archers if a.active]
        self.table.set_rows([[a.first_name, a.last_name, a.club,
                              a.default_bow_class.abbreviation or a.default_bow_class.name
                              if a.default_bow_class else None,
                              a.member_number,
                              Cell(a.active, chip=("Aktiv", "success") if a.active
                                   else ("Inaktiv", "danger"))] for a in visible],
                            [a.id for a in visible])
        clubs = {a.club.strip().lower() for a in archers if a.club}
        active = sum(a.active for a in archers)
        self.header.set_subtitle(f"{len(archers)} Schützen | {active} aktiv | "
                                 f"{len(clubs)} Vereine")
        self.on_selection(self.table.selected_ids())

    def _selected(self):
        return [self._archers[i] for i in self.table.selected_ids() if i in self._archers]

    # ------------------------------------------------------------ actions
    def on_selection(self, ids):
        n = len(ids)
        if n == 0:
            actions = []
        elif n == 1:
            actions = [Action("Bearbeiten", self.edit_item, tooltip="Schützen bearbeiten"),
                       Action("Löschen", self.delete_selected, "danger",
                              tooltip="Schützen löschen (mit Rückfrage)")]
        else:
            actions = [Action(f"{n} Schützen löschen", self.delete_selected, "danger",
                              tooltip="Alle ausgewählten Schützen löschen (mit Rückfrage)")]
        self.action_bar.set_actions(self.selection_info(n, "Schütze", "Schützen"), actions)

    def context_entries(self, row_id):
        a = self._archers.get(row_id)
        if a is None:
            return []
        return [("Bearbeiten", self.edit_item),
                ("Klasse ändern …", self.change_class),
                ("Als inaktiv markieren" if a.active else "Wieder aktivieren",
                 lambda: self.set_active(not a.active)),
                None,
                ("Löschen", self.delete_selected)]

    def new_item(self):
        dlg = ArcherDialog(parent=self)
        if dlg.exec() and dlg.saved_id:
            Toast.show(self, f"{dlg.saved_name} gespeichert", Toast.SUCCESS)
            self.refresh()
            self.table.select_ids([dlg.saved_id])

    def edit_item(self, *_):
        sel = self._selected()
        if not sel:
            return
        dlg = ArcherDialog(record=sel[0], parent=self)
        if dlg.exec() and dlg.saved_id:
            Toast.show(self, f"{dlg.saved_name} gespeichert", Toast.SUCCESS)
            self.refresh()
            self.table.select_ids([dlg.saved_id])

    def change_class(self):
        sel = self._selected()
        if not sel:
            return
        options = [("(keine)", None)] + [(bc.name, bc.id) for bc in md.list_bow_classes()]
        cid = choose(self, "Klasse ändern",
                     f"Standardklasse für {len(sel)} Schützen:" if len(sel) > 1
                     else f"Standardklasse für {sel[0].first_name} {sel[0].last_name}:",
                     options, sel[0].default_bow_class_id)
        if cid is choose.CANCELLED:
            return
        for a in sel:
            md.save_archer({"default_bow_class_id": cid}, a.id)
        Toast.show(self, "Klasse geändert", Toast.SUCCESS)
        self.refresh()

    def set_active(self, active: bool):
        sel = self._selected()
        for a in sel:
            md.set_archer_active(a.id, active)
        Toast.show(self, f"{len(sel)} Schützen {'aktiviert' if active else 'deaktiviert'}",
                   Toast.SUCCESS)
        self.refresh()

    def delete_selected(self):
        sel = self._selected()
        if not sel:
            return
        names = ", ".join(f"{a.first_name} {a.last_name}" for a in sel[:3]) + \
            (f" und {len(sel) - 3} weitere" if len(sel) > 3 else "")
        if not ConfirmDialog.ask(self, f"{len(sel)} Schützen löschen?" if len(sel) > 1
                                 else "Schützen löschen?",
                                 f"{names} wird endgültig gelöscht."):
            return
        with busy():
            blocked = [a for a in sel if md.archer_has_tournaments(a.id)]
            for a in sel:
                if a not in blocked:
                    md.delete_archer(a.id)
        deleted = len(sel) - len(blocked)
        if blocked and ConfirmDialog.ask(
                self, "Turnierdaten vorhanden",
                f"{len(blocked)} Schützen haben bereits an Turnieren teilgenommen und können "
                "nicht gelöscht werden, ohne Ergebnisse zu verlieren. Stattdessen als inaktiv "
                "markieren?", "Deaktivieren", destructive=False):
            for a in blocked:
                md.set_archer_active(a.id, False)
            Toast.show(self, f"{len(blocked)} Schützen deaktiviert", Toast.INFO)
        if deleted:
            Toast.show(self, f"{deleted} Schützen gelöscht", Toast.SUCCESS)
        self.refresh()

    # ------------------------------------------------------------ import / export
    def _import(self):
        res = run_import(self, ARCHER_IMPORT_FIELDS, "Schützen importieren")
        if res is None:
            return
        records, strategy = res
        try:
            with busy():
                r = md.import_archers(records, strategy)
        except Exception as exc:
            show_error(self, exc, "Import fehlgeschlagen")
            return
        Toast.show(self, f"Import abgeschlossen: {r['created']} neu, {r['updated']} "
                         f"aktualisiert, {r['skipped']} übersprungen", Toast.SUCCESS)
        self.refresh()

    def _export_sheets(self, filtered: bool):
        ids = self.table.visible_ids() if filtered else list(self._archers)
        rows = []
        for i in ids:
            a = self._archers[i]
            rows.append([a.last_name, a.first_name, a.birth_date, a.club, a.member_number,
                         a.default_bow_class.name if a.default_bow_class else None, a.email,
                         a.phone, "Ja" if a.active else "Nein"])
        return [("Schützen", EXPORT_HEADERS, rows)]
