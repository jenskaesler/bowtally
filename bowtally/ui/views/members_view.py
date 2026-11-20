# -*- coding: utf-8 -*-
"""Member management (global): master data, bank data and helper history."""
from datetime import date

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDoubleSpinBox,
                               QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QTabWidget,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from bowtally.io.importer import MEMBER_IMPORT_FIELDS
from bowtally.services import member_service as ms
from bowtally.services import tournament_service as ts
from bowtally.services.settings_service import (KEY_EMAIL_TPL_DATA_REQUEST,
                                                KEY_WHATSAPP_TPL_DATA_REQUEST)
from bowtally.services import ValidationError
from bowtally.ui import busy, button, show_error
from bowtally.ui.components.action_bar import Action
from bowtally.ui.components.confirm_dialog import ConfirmDialog
from bowtally.ui.components.data_table import Cell, ROW_HEIGHT
from bowtally.ui.components.empty_state import EmptyState
from bowtally.ui.components.form_field import DateField, Form, email_validator
from bowtally.ui.components.toast import Toast
from bowtally.ui.constants import SETTINGS_COMBO_W, SETTINGS_LABEL_W
from bowtally.ui.components.files_panel import FilesPanel
from bowtally.ui.components.half_height import keep_half_height
from bowtally.ui.dialogs.export_helper import export_button
from bowtally.ui.dialogs.import_dialog import run_import
from bowtally.ui.dialogs.record_dialog import RecordDialog
from bowtally.ui.utils.mailto import open_mailto
from bowtally.ui.utils.whatsapp import normalize_phone, open_whatsapp
from bowtally.ui.views import ListView

HEADERS = ["Mitgliedsnummer", "Name", "Ort", "E-Mail", "Status", "Turnierhelfer"]
# Base data only: bank data and birthday never leave the app through exports
EXPORT_HEADERS = ["Mitgliedsnummer", "Nachname", "Vorname", "Straße", "PLZ", "Ort", "Telefon",
                  "E-Mail", "Mitglied seit", "Gekündigt am", "Status", "Turnierhelfer"]
AUTO_ENTRY_TIP = "Automatisch erfasster Einsatz, nicht änderbar"
_HEADER_ALIGN = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter


def _hours_text(hours) -> str:
    return "–" if hours is None else f"{hours:.1f}".replace(".", ",")


def _iban_validator(value) -> str | None:
    return None if ms.is_valid_iban(value) else "Die IBAN ist ungültig"


class _HistoryEntryDialog(RecordDialog):
    """Add / edit a manual helper history entry, optionally linked to an existing tournament."""
    _default_size = (760, 520)
    _size_name = "HistoryEntryDialog_v2"

    def __init__(self, member_id: int, entry=None, parent=None):
        self._member_id, self._entry = member_id, entry
        super().__init__("Einsatz bearbeiten" if entry else "Einsatz hinzufügen", parent=parent)
        if entry:
            self.form.set_values({"tournament_id": entry.tournament_id,
                                  "tournament_name": entry.tournament_name, "date": entry.date,
                                  "role": entry.role, "hours": entry.hours})
        self._baseline = self.form.snapshot()
        self.form.fields["tournament_id"].widget.currentIndexChanged.connect(self._prefill)

    def _prefill(self):
        t = self._tournaments.get(self.form.values()["tournament_id"])
        if t:
            self.form.fields["tournament_name"].set_value(t.name)
            self.form.fields["date"].set_value(t.date)

    def _setup_form(self):
        hours = QDoubleSpinBox()
        hours.setDecimals(1)
        hours.setRange(0, 999)
        combo = QComboBox()
        combo.addItem("(kein Turnier)", None)
        self._tournaments = {t.id: t for t in ts.list_tournaments()}
        for t in self._tournaments.values():
            combo.addItem(f"{t.name} ({t.date:%d.%m.%Y})" if t.date else t.name, t.id)
        self.form.add("tournament_id", "Turnier (optional)", combo)
        self.form.add("tournament_name", "Turniername", QLineEdit(), required=True)
        self.form.add("date", "Datum", DateField())
        self.form.add("role", "Rolle/Aufgabe", QLineEdit())
        self.form.add("hours", "Stunden", hours)

    def _do_save(self) -> bool:
        try:
            if self._entry:
                ms.update_history(self._entry.id, self.form.values())
            else:
                ms.add_history(self._member_id, self.form.values())
        except Exception as exc:
            show_error(self, exc, "Einsatz konnte nicht gespeichert werden")
            return False
        return True


class MemberDialog(RecordDialog):
    """Create / edit a member: base data, bank data, helper history, notes and files."""
    _default_size = (698, 640)

    def __init__(self, record=None, parent=None):
        self._record = record
        self._loading = True       # while values are set, the consent date is not prefilled
        super().__init__("Neues Mitglied" if record is None else record.full_name, parent=parent)
        if record is None:
            values = {"member_number": ms.next_member_number(), "active": True}
        else:
            values = {k: getattr(record, k) for k in (*ms.TEXT_FIELDS, *ms.DATE_FIELDS,
                                                      *ms.BOOL_FIELDS)}
        self.form.set_values(values)
        self.bank_form.set_values(values)
        self.notes_form.set_values(values)
        self._loading = False
        self.form.set_row_visible("consent_date", self.form.fields["consent_given"].widget.isChecked())
        self._show_history_tab(self.form.fields["is_tournament_helper"].widget.isChecked())
        self._baseline = self._snapshot()
        self.saved_id: int | None = None
        self.saved_name: str = ""

    def _setup_form(self):
        f = self.form
        f.add("member_number", "Mitgliedsnummer", QLineEdit(), required=True, short=True)
        f.add("first_name", "Vorname", QLineEdit(), required=True)
        f.add("last_name", "Nachname", QLineEdit(), required=True)
        f.add("street", "Straße", QLineEdit())
        f.add("postal_code", "PLZ", QLineEdit(), short=True)
        f.add("city", "Ort", QLineEdit())
        f.add("phone", "Telefon", QLineEdit(), short=True)
        f.add("email", "E-Mail", QLineEdit(), validator=email_validator)
        f.add("birthday", "Geburtstag", DateField())
        f.add("member_since", "Mitglied seit", DateField())
        f.add("cancelled_on", "Gekündigt zum", DateField())
        consent = QCheckBox("Einwilligung Datenverarbeitung")
        helper = QCheckBox("Ist Helfer")
        f.add("consent_given", "Einwilligung", consent)
        f.add("consent_date", "Datum der Einwilligung", DateField())
        f.add("info_by_mail", "Info per E-Mail", QCheckBox("Vereinsinfos per E-Mail erhalten"))
        f.add("is_tournament_helper", "Helfer", helper)
        f.add("active", "Status", QCheckBox("Aktiv"))
        consent.toggled.connect(self._on_consent_toggled)
        helper.toggled.connect(self._show_history_tab)

        self.bank_form = Form(label_width=SETTINGS_LABEL_W, combo_width=SETTINGS_COMBO_W)
        b = self.bank_form
        b.add("account_holder", "Kontoinhaber", QLineEdit(),
              trailing=button("Basisdaten übernehmen", self._copy_account_holder))
        b.add("iban", "IBAN", QLineEdit(), validator=_iban_validator)
        b.add("bic", "BIC (optional)", QLineEdit())
        b.add("bank_name", "Name der Bank", QLineEdit())
        b.add("sepa_direct_debit", "Einzugsermächtigung", QCheckBox("Einzugsermächtigung erteilt"))
        b.add("sepa_mandate_ref", "SEPA-Mandatsreferenz", QLineEdit())
        b.add("sepa_mandate_date", "Datum der Mandatserteilung", DateField())

        self._tabs = QTabWidget()
        self._body_layout.removeWidget(self.form)
        self._tabs.addTab(self.form, "Basisdaten")
        self._tabs.addTab(self.bank_form, "Bankverbindung")
        self._tabs.addTab(self._build_history(), "Helferhistorie")
        self._tabs.addTab(self._build_notes(), "Notizen")
        self._files_panel = FilesPanel(
            None if self._record is None else self._record.id, "Mitglied", ms.list_member_files,
            ms.add_member_file, ms.remove_member_file, ms.member_file_path)
        self._tabs.addTab(self._files_panel, "Dokumente")
        self._body_layout.addWidget(self._tabs)

    def _on_consent_toggled(self, on: bool):
        self.form.set_row_visible("consent_date", on)
        if not self._loading:      # a click: prefill today / forget the date
            self.form.fields["consent_date"].set_value(date.today() if on else None)

    def _show_history_tab(self, show: bool):
        index = self._tabs.indexOf(self._history_page)
        self._tabs.setTabVisible(index, show)
        bar = self._tabs.tabBar()          # re-setting the text refreshes Qt's cached tab sizes
        for i in range(bar.count()):
            bar.setTabText(i, bar.tabText(i))

    def _copy_account_holder(self):
        values = self.form.values()
        self.bank_form.fields["account_holder"].set_value(
            f"{values['first_name']} {values['last_name']}".strip())

    # ---------------------------------------------------------------- helper history
    def _build_history(self) -> QWidget:
        page = self._history_page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        if self._record is None:
            lay.addWidget(QLabel("Die Helferhistorie kann nach dem ersten Speichern gepflegt "
                                 "werden.", objectName="pageSubtitle"))
            return page
        self._history = QTableWidget(0, 4)
        t = self._history
        t.setHorizontalHeaderLabels(["Turnier", "Datum", "Rolle/Aufgabe", "Stunden"])
        t.verticalHeader().hide()
        t.verticalHeader().setDefaultSectionSize(ROW_HEIGHT)
        t.setMinimumHeight(220)
        t.setShowGrid(False)
        t.setAlternatingRowColors(True)
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        t.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        t.horizontalHeader().setStretchLastSection(True)
        t.horizontalHeader().setDefaultAlignment(_HEADER_ALIGN)
        t.itemSelectionChanged.connect(self._update_history_buttons)
        self._btn_edit = button("Bearbeiten", self._edit_entry)
        self._btn_delete = button("Löschen", self._delete_entry)
        buttons = QHBoxLayout()
        buttons.addWidget(button("Einsatz hinzufügen", self._add_entry))
        buttons.addWidget(self._btn_edit)
        buttons.addWidget(self._btn_delete)
        buttons.addStretch()
        lay.addWidget(t, 1)
        lay.addLayout(buttons)
        self._reload_history()
        return page

    def _reload_history(self):
        self._entries = {e.id: e for e in ms.list_history(self._record.id)}
        t = self._history
        t.setRowCount(len(self._entries))
        for row, e in enumerate(self._entries.values()):
            texts = [e.tournament_name, f"{e.date:%d.%m.%Y}" if e.date else "–",
                     e.role or "–", _hours_text(e.hours)]
            for col, text in enumerate(texts):
                item = QTableWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole, e.id)
                if not ms.is_manual_entry(e):
                    item.setToolTip(AUTO_ENTRY_TIP)
                t.setItem(row, col, item)
        self._update_history_buttons()

    def _selected_entry(self):
        row = self._history.currentRow()
        item = self._history.item(row, 0) if row >= 0 else None
        return self._entries[item.data(Qt.ItemDataRole.UserRole)] if item else None

    def _update_history_buttons(self):
        entry = self._selected_entry()
        editable = entry is not None and ms.is_manual_entry(entry)
        for btn in (self._btn_edit, self._btn_delete):
            btn.setEnabled(editable)
            btn.setToolTip("" if editable else AUTO_ENTRY_TIP)

    def _add_entry(self):
        if _HistoryEntryDialog(self._record.id, parent=self).exec():
            self._reload_history()

    def _edit_entry(self):
        if _HistoryEntryDialog(self._record.id, self._selected_entry(), self).exec():
            self._reload_history()

    def _delete_entry(self):
        if not ConfirmDialog.ask(self, "Einsatz löschen?", "Der Einsatz wird endgültig gelöscht."):
            return
        try:
            ms.delete_history(self._selected_entry().id)
        except Exception as exc:
            show_error(self, exc, "Einsatz konnte nicht gelöscht werden")
            return
        self._reload_history()

    # ---------------------------------------------------------------- notes
    def _build_notes(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        self.notes_form = Form()
        self.notes_form.set_labels_on_top()
        notes = QPlainTextEdit()
        self.notes_form.add("notes", "Notizen", notes)
        lay.addWidget(self.notes_form)
        lay.addStretch()
        keep_half_height(page, notes)
        return page

    # ---------------------------------------------------------------- save
    def _snapshot(self) -> tuple:
        return self.form.snapshot() + self.bank_form.snapshot() + self.notes_form.snapshot()

    def _is_dirty(self) -> bool:
        return self._snapshot() != self._baseline

    def _on_save(self):
        basis_ok, bank_ok = self.form.validate(), self.bank_form.validate()
        if not (basis_ok and bank_ok):
            self._tabs.setCurrentIndex(0 if not basis_ok else 1)
            return
        if self._do_save():
            self.accept()

    def _do_save(self) -> bool:
        values = {**self.form.values(), **self.bank_form.values(), **self.notes_form.values()}
        if not values["consent_given"]:
            values["consent_date"] = None
        if (values["iban"] or values["birthday"]) and not values["consent_given"] \
                and not ConfirmDialog.ask(
                    self, "Einwilligung fehlt",
                    "IBAN oder Geburtstag sind hinterlegt, aber die Einwilligung zur "
                    "Datenverarbeitung ist nicht angekreuzt.\n\nTrotzdem speichern?",
                    "Trotzdem speichern", destructive=False):
            return False
        try:
            with busy():
                member = (ms.create_member(values) if self._record is None
                          else ms.update_member(self._record.id, values))
        except Exception as exc:
            show_error(self, exc, "Mitglied konnte nicht gespeichert werden")
            return False
        self.saved_id, self.saved_name = member.id, f"{member.first_name} {member.last_name}"
        return True


class MembersView(ListView):
    def __init__(self, parent=None):
        empty = EmptyState("users", "Keine Mitglieder",
                           "Lege neue Mitglieder an oder importiere eine Mitgliederliste.",
                           "Neues Mitglied")
        super().__init__("Mitglieder", HEADERS, empty,
                         search_placeholder="Name oder Mitgliedsnummer …")
        empty.actionTriggered.connect(self.new_item)
        self.header.add(button("Neues Mitglied", self.new_item, "primary",
                               "Neues Mitglied anlegen (Strg+N)"))

        footer = QWidget()
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(0, 4, 0, 0)
        self._show_inactive = QCheckBox("Inaktive Mitglieder anzeigen")
        self._show_inactive.setChecked(
            QSettings("BowTally", "BowTally").value("members/show_inactive", False, type=bool))
        self._show_inactive.toggled.connect(self.refresh)
        self._show_inactive.toggled.connect(
            lambda v: QSettings("BowTally", "BowTally").setValue("members/show_inactive", v))
        fl.addWidget(self._show_inactive)
        fl.addStretch()
        fl.addWidget(export_button(self, "mitglieder", self._export_sheets,
                                   lambda: len(self.table.visible_ids())
                                   if self.table.is_filtered() else None))
        fl.addWidget(button("Importieren", self._import,
                            tooltip="Mitglieder aus CSV, Excel oder OpenDocument importieren"))
        self.main_layout.insertWidget(2, footer)
        self.table.activated.connect(self.edit_item)
        self._rows: dict[int, object] = {}

    # ---------------------------------------------------------------- data
    def refresh(self):
        with busy():
            members = ms.list_members(include_inactive=self._show_inactive.isChecked())
        self._rows = {m.id: m for m in members}
        self.table.set_rows([[
            m.member_number,
            m.full_name if m.active else f"{m.full_name} (inaktiv)",
            m.city or "",
            m.email or "",
            Cell(ms.member_status(m), chip=("Aktiv", "success") if ms.member_status(m) == "Aktiv"
                 else ("Gekündigt", "muted")),
            "Ja" if m.is_tournament_helper else "-",
        ] for m in members], [m.id for m in members])
        self.header.set_subtitle(f"{len(members)} Mitglieder")
        self.on_selection(self.table.selected_ids())

    # ---------------------------------------------------------------- selection
    def _entries(self, row_id) -> list:
        m = self._rows[row_id]
        entries = [("Bearbeiten", self.edit_item)]
        if m.email:
            entries.append(("Datenauskunft senden", lambda: self._send_data_request(row_id)))
        if normalize_phone(m.phone):
            entries.append(("WhatsApp: Datenauskunft senden",
                            lambda: self._send_data_request_whatsapp(row_id)))
        entries.append(("Als inaktiv markieren" if m.active else "Wieder aktivieren",
                        lambda: self._set_active(row_id, not m.active)))
        return entries + [None, ("Löschen", self.delete_selected)]

    def context_entries(self, row_id):
        return self._entries(row_id) if row_id in self._rows else []

    def on_selection(self, ids: list):
        if not ids:
            self.action_bar.set_actions("", [])
            return
        actions = [Action("Bearbeiten", self.edit_item, tooltip="Mitglied bearbeiten"),
                   Action("Löschen", self.delete_selected, "danger")]
        self.action_bar.set_actions(self.selection_info(len(ids), "Mitglied", "Mitglieder"), actions)

    # ---------------------------------------------------------------- new / edit
    def new_item(self):
        self._open_dialog(MemberDialog(parent=self))

    def edit_item(self, *_):
        ids = self.table.selected_ids()
        if ids and ids[0] in self._rows:
            self._open_dialog(MemberDialog(self._rows[ids[0]], parent=self))

    def _open_dialog(self, dlg: MemberDialog):
        if dlg.exec() and dlg.saved_id:
            Toast.show(self, f"{dlg.saved_name} gespeichert", Toast.SUCCESS)
            self.refresh()
            self.table.select_ids([dlg.saved_id])

    # ---------------------------------------------------------------- actions
    def delete_selected(self):
        ids = [i for i in self.table.selected_ids() if i in self._rows]
        if not ids:
            return
        names = ", ".join(self._rows[i].full_name for i in ids)
        if not ConfirmDialog.ask(self, "Mitglied löschen?",
                                 f"{names}\n\nDas Mitglied wird endgültig gelöscht.",
                                 "Löschen", destructive=True):
            return
        blocked = []
        with busy():
            for i in ids:
                try:
                    ms.delete_member(i)
                except ValidationError:
                    blocked.append(i)
        if blocked and ConfirmDialog.ask(
                self, "Turnierdaten vorhanden",
                f"{len(blocked)} Mitglieder waren bereits bei Turnieren eingesetzt und können "
                "nicht gelöscht werden. Stattdessen als inaktiv markieren?",
                "Deaktivieren", destructive=False):
            for i in blocked:
                ms.set_active(i, False)
        if len(ids) > len(blocked):
            Toast.show(self, f"{len(ids) - len(blocked)} Mitglieder gelöscht", Toast.SUCCESS)
        self.refresh()

    def _set_active(self, member_id: int, active: bool):
        ms.set_active(member_id, active)
        self.refresh()

    def _send_data_request(self, member_id: int):
        m = self._rows[member_id]
        open_mailto(KEY_EMAIL_TPL_DATA_REQUEST, m.email, {
            "name": f"{m.first_name} {m.last_name}", "first_name": m.first_name,
            "last_name": m.last_name, "daten": ms.data_summary(member_id),
        }, self, as_draft=True)

    def _send_data_request_whatsapp(self, member_id: int):
        m = self._rows[member_id]
        open_whatsapp(KEY_WHATSAPP_TPL_DATA_REQUEST, m.phone, {
            "name": f"{m.first_name} {m.last_name}", "first_name": m.first_name,
            "last_name": m.last_name, "daten": ms.data_summary(member_id),
        }, self)

    # ---------------------------------------------------------------- import / export
    def _import(self):
        res = run_import(self, MEMBER_IMPORT_FIELDS, "Mitglieder importieren")
        if res is None:
            return
        records, strategy = res
        try:
            with busy():
                r = ms.import_members(records, strategy)
        except Exception as exc:
            show_error(self, exc, "Import fehlgeschlagen")
            return
        Toast.show(self, f"Import abgeschlossen: {r['created']} neu, {r['updated']} "
                         f"aktualisiert, {r['skipped']} übersprungen", Toast.SUCCESS)
        self.refresh()

    def _export_sheets(self, filtered: bool):
        ids = self.table.visible_ids() if filtered else list(self._rows)
        return [("Mitglieder", EXPORT_HEADERS, [
            [m.member_number, m.last_name, m.first_name, m.street, m.postal_code, m.city,
             m.phone, m.email, m.member_since, m.cancelled_on, ms.member_status(m),
             "Ja" if m.is_tournament_helper else "Nein"]
            for m in (self._rows[i] for i in ids if i in self._rows)])]
