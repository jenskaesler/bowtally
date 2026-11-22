# -*- coding: utf-8 -*-
"""Vereinsinventar: Liste mit Kategorie-Filter und ein Dialog je Artikel (Tabs)."""
from datetime import date

from PySide6.QtCore import QSettings, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QFileDialog, QHBoxLayout,
                               QLabel, QLineEdit, QPlainTextEdit, QSizePolicy, QSpinBox,
                               QTabWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from bowtally.io.importer import INVENTORY_IMPORT_FIELDS
from bowtally.services import inventory_service as inv
from bowtally.ui import busy, button, show_error
from bowtally.ui.components.action_bar import Action
from bowtally.ui.components.confirm_dialog import ConfirmDialog
from bowtally.ui.components.data_table import (Cell, ROW_HEIGHT, optional, optional_columns,
                                               optional_values)
from bowtally.ui.components.empty_state import EmptyState
from bowtally.ui.components.files_panel import FilesPanel
from bowtally.ui.components.form_field import DateField, Form
from bowtally.ui.components.toast import Toast
from bowtally.ui.dialogs.export_helper import export_button, open_path
from bowtally.ui.dialogs.import_dialog import run_import
from bowtally.ui.dialogs.record_dialog import RecordDialog
from bowtally.ui.views import ListView
from bowtally.ui.views.fees_view import AmountField
from bowtally.ui.views.participants_view import money

HEADERS = ["Bezeichnung", "Kategorie", "Größe", "Einzelpreis", "Anzahl", "Gesamtpreis", "Parcours",
           "Status"]
# existing data fields that can be shown on demand (header right-click)
INVENTORY_OPTIONAL = [
    (optional("shop_url", "Shop-Link"), lambda i: i.shop_url),
    (optional("notes", "Notizen"), lambda i: i.notes),
]
_HEADER_ALIGN = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter


def _money_cell(amount: float) -> Cell:
    return Cell(amount, text=money(amount))


class _RepairDialog(RecordDialog):
    """Add / edit one repair entry of an item."""
    _default_size = (640, 400)

    def __init__(self, item_id: int, repair=None, parent=None):
        self._item_id, self._repair = item_id, repair
        super().__init__("Reparatur bearbeiten" if repair else "Reparatur hinzufügen", parent=parent)
        self.form.set_values(
            {"date": repair.date, "description": repair.description, "cost": repair.cost,
             "performed_by": repair.performed_by, "invoice_file_id": repair.invoice_file_id}
            if repair else {"date": date.today()})
        self._baseline = self.form.snapshot()

    def _setup_form(self):
        self._invoice = QComboBox()
        self._invoice.addItem("(keine)", None)
        for stored in inv.list_inventory_files(self._item_id):
            self._invoice.addItem(stored.filename, stored.id)
        self.form.add("date", "Datum", DateField(), required=True)
        self.form.add("description", "Beschreibung", QLineEdit())
        self.form.add("cost", "Kosten", AmountField(), required=True,
                      validator=lambda v: None if v and v > 0 else "Kosten müssen größer als 0 sein")
        self.form.add("performed_by", "Durchgeführt von", QLineEdit())
        self.form.add("invoice_file_id", "Rechnung", self._invoice, trailing=button(
            "Datei hinzufügen …", self._add_invoice,
            tooltip="Rechnung in die Dokumente des Artikels legen und hier verknüpfen"))

    def _add_invoice(self):
        path, _ = QFileDialog.getOpenFileName(self, "Rechnung auswählen")
        if not path:
            return
        try:
            with busy():
                stored = inv.add_inventory_file(self._item_id, path)
        except Exception as exc:
            show_error(self, exc, "Rechnung konnte nicht hinzugefügt werden")
            return
        self._invoice.addItem(stored.filename, stored.id)
        self._invoice.setCurrentIndex(self._invoice.count() - 1)

    def _do_save(self) -> bool:
        values = {**self.form.values(), "invoice_file_id": self._invoice.currentData()}
        try:
            inv.save_repair(values, self._repair.id if self._repair else None, self._item_id)
        except Exception as exc:
            show_error(self, exc, "Reparatur konnte nicht gespeichert werden")
            return False
        return True


class InventoryItemDialog(RecordDialog):
    """Create / edit an item: base data, notes, documents and repair costs."""
    _default_size = (680, 560)

    def __init__(self, record=None, parent=None):
        self._record = record
        super().__init__("Neuer Artikel" if record is None else record.name, parent=parent)
        keys = (*self.form.fields, *self.notes_form.fields)
        self.form.set_values({"quantity": 1, "unit_price": 0, "active": True} if record is None else
                             {k: getattr(record, k, None) for k in keys})
        self.notes_form.set_values({} if record is None else {"notes": record.notes})
        self._update_total()
        self._update_open_button()
        self._baseline = self._snapshot()
        self.saved_id: int | None = None

    def _setup_form(self):
        f = self.form
        self._category = QComboBox()
        self._category.addItem("(keine)", None)
        for c in inv.list_categories():
            self._category.addItem(c.name, c.id)
        self._open_button = button("Öffnen", self._open_shop_link,
                                   tooltip="Link im Browser öffnen")
        quantity = QSpinBox()
        quantity.setRange(0, 99999)
        f.add("name", "Bezeichnung", QLineEdit(), required=True)
        f.add("category_id", "Kategorie", self._category)
        f.add("size", "Größe", QLineEdit())
        f.add("shop_url", "Link zum Shop", QLineEdit(), trailing=self._open_button)
        f.add("unit_price", "Einzelpreis", AmountField(), required=True)
        f.add("quantity", "Anzahl", quantity)
        f.add("total", "Gesamtpreis", QLineEdit(), short=True)
        f.add("use_in_course", "Parcoursplanung", QCheckBox("Für Parcoursplanung verwenden"))
        f.add("active", "Status", QCheckBox("Aktiv"))
        f.fields["total"].set_read_only(True)
        f.fields["shop_url"].widget.textChanged.connect(self._update_open_button)
        f.fields["unit_price"].widget.valueChanged.connect(self._update_total)
        quantity.valueChanged.connect(self._update_total)

        self._tabs = QTabWidget()
        self._body_layout.removeWidget(f)
        self._tabs.addTab(f, "Stammdaten")
        self._tabs.addTab(self._build_notes(), "Notizen")
        self._files_panel = FilesPanel(
            None if self._record is None else self._record.id, "Artikel",
            inv.list_inventory_files, inv.add_inventory_file, inv.remove_inventory_file,
            inv.inventory_file_path, inv.invoice_hints)
        self._tabs.addTab(self._files_panel, "Dokumente")
        self._tabs.addTab(self._build_repairs(), "Reparaturkosten")
        self._body_layout.addWidget(self._tabs)
        self._tabs.currentChanged.connect(self._sync_files_and_repairs)

    def _sync_files_and_repairs(self, *_):
        """Invoices are added / removed on one tab and shown on the other."""
        if self._record is not None:
            self._files_panel.reload()
            self._reload_repairs()

    def _update_total(self, *_):
        values = self.form.values()
        self.form.fields["total"].set_value(money(values["unit_price"] * values["quantity"]))

    # ---------------------------------------------------------------- shop link
    def _shop_url(self) -> QUrl | None:
        url = QUrl.fromUserInput(self.form.fields["shop_url"].value())
        return url if url.scheme() in ("http", "https") else None

    def _update_open_button(self, *_):
        self._open_button.setEnabled(self._shop_url() is not None)

    def _open_shop_link(self):
        url = self._shop_url()
        if url is not None:
            QDesktopServices.openUrl(url)

    # ---------------------------------------------------------------- notes
    def _build_notes(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        self.notes_form = Form()
        self.notes_form.set_labels_on_top()
        notes = QPlainTextEdit()
        notes.setMinimumHeight(110)
        field = self.notes_form.add("notes", "Notizen", notes)
        field.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        lay.addWidget(self.notes_form, 1)      # equal stretch for form and spacer: notes get half
        lay.addStretch(1)
        return page

    # ---------------------------------------------------------------- repairs
    def _build_repairs(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        if self._record is None:
            lay.addWidget(QLabel("Reparaturen können nach dem ersten Speichern erfasst werden.",
                                 objectName="pageSubtitle"))
            lay.addStretch()
            return page
        self._repairs = t = QTableWidget(0, 5)
        t.setHorizontalHeaderLabels(["Datum", "Beschreibung", "Kosten", "Durchgeführt von",
                                     "Rechnung"])
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
        t.itemSelectionChanged.connect(self._update_repair_buttons)
        t.itemDoubleClicked.connect(lambda _item: self._open_invoice())
        self._btn_edit = button("Bearbeiten", self._edit_repair)
        self._btn_invoice = button("Rechnung öffnen", self._open_invoice)
        self._btn_delete = button("Löschen", self._delete_repair)
        buttons = QHBoxLayout()
        buttons.addWidget(button("Reparatur hinzufügen", self._add_repair))
        buttons.addWidget(self._btn_edit)
        buttons.addWidget(self._btn_invoice)
        buttons.addWidget(self._btn_delete)
        buttons.addStretch()
        lay.addWidget(t, 1)
        lay.addLayout(buttons)
        self._reload_repairs()
        return page

    def _reload_repairs(self):
        self._repair_rows = {r.id: r for r in inv.list_repairs(self._record.id)}
        t = self._repairs
        t.setRowCount(len(self._repair_rows))
        for row, r in enumerate(self._repair_rows.values()):
            texts = [f"{r.date:%d.%m.%Y}", r.description or "–", money(r.cost),
                     r.performed_by or "–", r.invoice_file.filename if r.invoice_file else "–"]
            for col, text in enumerate(texts):
                item = QTableWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole, r.id)
                t.setItem(row, col, item)
        self._update_repair_buttons()

    def _selected_repair(self):
        item = self._repairs.item(self._repairs.currentRow(), 0)
        return self._repair_rows[item.data(Qt.ItemDataRole.UserRole)] if item else None

    def _update_repair_buttons(self):
        repair = self._selected_repair()
        for btn in (self._btn_edit, self._btn_delete):
            btn.setEnabled(repair is not None)
        self._btn_invoice.setEnabled(repair is not None and repair.invoice_file is not None)

    def _open_invoice(self):
        repair = self._selected_repair()
        if repair is not None and repair.invoice_file is not None:
            open_path(self, inv.inventory_file_path(repair.invoice_file))

    def _add_repair(self):
        if _RepairDialog(self._record.id, parent=self).exec():
            self._reload_repairs()

    def _edit_repair(self):
        if _RepairDialog(self._record.id, self._selected_repair(), self).exec():
            self._reload_repairs()

    def _delete_repair(self):
        if not ConfirmDialog.ask(self, "Reparatur löschen?",
                                 "Der Eintrag wird endgültig gelöscht."):
            return
        try:
            inv.delete_repair(self._selected_repair().id)
        except Exception as exc:
            show_error(self, exc, "Reparatur konnte nicht gelöscht werden")
            return
        self._reload_repairs()

    # ---------------------------------------------------------------- save
    def _snapshot(self) -> tuple:
        return self.form.snapshot() + self.notes_form.snapshot()

    def _is_dirty(self) -> bool:
        return self._snapshot() != self._baseline

    def _on_save(self):
        self._tabs.setCurrentIndex(0)      # the only validated fields live on the first tab
        super()._on_save()

    def _do_save(self) -> bool:
        values = {**self.form.values(), **self.notes_form.values(),
                  "category_id": self._category.currentData()}   # form value is text without categories
        try:
            with busy():
                item = inv.save_item(values, self._record.id if self._record else None)
        except Exception as exc:
            show_error(self, exc, "Artikel konnte nicht gespeichert werden")
            return False
        self.saved_id = item.id
        return True


class InventoryView(ListView):
    def __init__(self, parent=None):
        empty = EmptyState("inbox", "Kein Inventar vorhanden",
                           "Lege Artikel an oder importiere eine Liste.", "Neuer Artikel")
        super().__init__("Inventar", HEADERS + optional_columns(INVENTORY_OPTIONAL), empty,
                         search_placeholder="Bezeichnung, Kategorie oder Größe …", parent=parent)
        empty.actionTriggered.connect(self.new_item)
        self.header.add(button("Neuer Artikel", self.new_item, "primary"))
        self.table.activated.connect(self.edit_item)
        self._items: dict = {}

        self._show_active = QCheckBox("Aktives Inventar anzeigen")
        # new key: the old "inventory/show_active" was left at false by earlier test runs
        self._show_active.setChecked(
            QSettings("BowTally", "BowTally").value("inventory/only_active", True, type=bool))
        self._show_active.toggled.connect(self.refresh)
        self._show_active.toggled.connect(
            lambda v: QSettings("BowTally", "BowTally").setValue("inventory/only_active", v))

        footer = QWidget()
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(0, 4, 0, 0)
        fl.addWidget(self._show_active)
        fl.addStretch()
        fl.addWidget(export_button(self, "inventar", self._export_sheets,
                                   lambda: len(self.table.visible_ids())
                                   if self.table.is_filtered() else None))
        fl.addWidget(button("Importieren", self._import,
                            tooltip="Inventar aus CSV, Excel oder OpenDocument importieren"))
        self.main_layout.insertWidget(2, footer)

        self._category_filter = QComboBox()
        self._category_filter.setMinimumWidth(180)
        self._category_filter.currentIndexChanged.connect(lambda *_: self.refresh())
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Kategorie"))
        bar.addWidget(self._category_filter)
        bar.addStretch()
        self.main_layout.insertLayout(1, bar)

    def _load_categories(self):
        combo, current = self._category_filter, self._category_filter.currentData()
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("Alle", None)
        for c in inv.list_categories():
            combo.addItem(c.name, c.id)
        combo.setCurrentIndex(max(combo.findData(current), 0))
        combo.blockSignals(False)

    def refresh(self):
        self._load_categories()
        items = inv.list_items(category_id=self._category_filter.currentData(),
                               active_only=self._show_active.isChecked())
        self._items = {i.id: i for i in items}
        self.table.set_rows([[
            i.name, i.category.name if i.category else "", i.size or "",
            _money_cell(i.unit_price), i.quantity, _money_cell(inv.item_total(i)),
            "Ja" if i.use_in_course else "–",
            Cell(i.active, chip=("Aktiv", "success") if i.active else ("Inaktiv", "danger")),
        ] + optional_values(INVENTORY_OPTIONAL, i) for i in items], [i.id for i in items])
        self.header.set_subtitle(f"{len(items)} Artikel")
        self.on_selection(self.table.selected_ids())

    def showEvent(self, e):
        super().showEvent(e)
        self.refresh()

    def on_selection(self, ids):
        item = self._items.get(self.table.selected_id())
        if item is None:
            self.action_bar.set_actions("", [])
            return
        self.action_bar.set_actions(item.name, [
            Action("Bearbeiten", self.edit_item),
            Action("Löschen", self.delete_item, "danger"),
        ])

    def context_entries(self, row_id):
        item = self._items.get(row_id)
        if item is None:
            return []
        return [("Bearbeiten", self.edit_item, True),
                ("Deaktivieren" if item.active else "Aktivieren", self.toggle_active, True),
                None, ("Löschen", self.delete_item, True)]

    def toggle_active(self):
        item = self._items.get(self.table.selected_id())
        if item is not None:
            inv.set_item_active(item.id, not item.active)
            self.refresh()

    def new_item(self):
        self._open_dialog(InventoryItemDialog(parent=self))

    def edit_item(self, *_):
        item = self._items.get(self.table.selected_id())
        if item is not None:
            self._open_dialog(InventoryItemDialog(item, parent=self))

    def _open_dialog(self, dlg: InventoryItemDialog):
        if dlg.exec():
            self.refresh()
            if dlg.saved_id:
                self.table.select_ids([dlg.saved_id])

    def delete_item(self):
        item = self._items.get(self.table.selected_id())
        if item is None or not ConfirmDialog.ask(
                self, "Artikel löschen?", f"„{item.name}“ wird mit allen Dokumenten und "
                "Reparaturen endgültig gelöscht.", "Löschen", destructive=True):
            return
        try:
            inv.delete_item(item.id)
        except Exception as exc:
            show_error(self, exc, "Löschen fehlgeschlagen")
            return
        Toast.show(self, f"„{item.name}“ gelöscht", Toast.SUCCESS)
        self.refresh()

    def _export_sheets(self, filtered: bool):
        ids = self.table.visible_ids() if filtered else list(self._items)
        return [("Inventar", inv.EXPORT_HEADERS,
                 inv.export_rows([self._items[i] for i in ids if i in self._items]))]

    def _import(self):
        res = run_import(self, INVENTORY_IMPORT_FIELDS, "Inventar importieren")
        if res is None:
            return
        records, strategy = res
        try:
            with busy():
                r = inv.import_items(records, strategy)
        except Exception as exc:
            show_error(self, exc, "Import fehlgeschlagen")
            return
        Toast.show(self, f"Import abgeschlossen: {r['created']} neu, {r['updated']} "
                         f"aktualisiert, {r['skipped']} übersprungen", Toast.SUCCESS)
        self.refresh()
