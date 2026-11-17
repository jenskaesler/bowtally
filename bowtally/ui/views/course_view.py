# -*- coding: utf-8 -*-
"""Parcours-Planung: list of course targets for the active tournament, with drag-drop reorder."""
from PySide6.QtWidgets import (QComboBox, QDoubleSpinBox, QHBoxLayout, QLabel, QLineEdit,
                               QPlainTextEdit, QPushButton, QSpinBox, QTabWidget, QWidget)

from bowtally.services import course_service as cs
from bowtally.services import inventory_service as inv
from bowtally.services import tournament_service as ts
from bowtally.ui import busy, button, show_error, theme
from bowtally.ui.components.action_bar import Action
from bowtally.ui.components.data_table import Cell
from bowtally.ui.components.empty_state import EmptyState
from bowtally.ui.components.help_link import help_link
from bowtally.ui.components.toast import Toast
from bowtally.ui.components.confirm_dialog import ConfirmDialog
from bowtally.ui.components.confirm_dialog import choose
from bowtally.ui.context import context
from bowtally.ui.dialogs.record_dialog import RecordDialog
from bowtally.ui.views import ListView
from bowtally.ui.views.fees_view import AmountField
from bowtally.ui.views.participants_view import money

MATERIAL_HEADERS = ["Artikel", "Angefordert", "Bestand", "Status", "Einzelpreis", "Summe", "Typ"]
HEADERS =["Nr.", "Tier / Ziel", "Distanz (m)", "Pfeilstopp", "Gelände", "Max. Gruppe", "Helfernotiz"]
ARROW_STOPS = ["", "Klasse 1", "Klasse 2", "Klasse 3", "Klasse 4", "Klasse 5"]
TERRAIN_TYPES = ["", "Flach", "Hang", "Wald", "Wiese", "Wasser", "Hügel"]


class CourseTargetDialog(RecordDialog):
    _default_size = (780, 640)
    _size_name = "CourseTargetDialog_v2"

    def __init__(self, record=None, parent=None):
        self._record = record
        super().__init__("Neues Ziel" if record is None else "Ziel bearbeiten", parent=parent)
        self.set_left_footer_widget(self._inv_btn)
        if record:
            self.form.set_values({
                "number": record.number,
                "animal_name": record.animal_name or "",
                "distance_m": record.distance_m or 0.0,
                "arrow_stop_class": record.arrow_stop_class or "",
                "terrain_type": record.terrain_type or "",
                "max_group_size": record.max_group_size or 0,
                "helper_note": record.helper_note or "",
            })
        self._baseline = self.form.snapshot()
        self.saved_id: int | None = None

    def _setup_form(self):
        num = QSpinBox()
        num.setRange(1, 999)
        dist = QDoubleSpinBox()
        dist.setRange(0, 999)
        dist.setDecimals(1)
        dist.setSuffix(" m")
        arrow = QComboBox()
        arrow.setEditable(True)
        arrow.addItems(ARROW_STOPS)
        terrain = QComboBox()
        terrain.setEditable(True)
        terrain.addItems(TERRAIN_TYPES)
        grp = QSpinBox()
        grp.setRange(0, 20)
        grp.setSpecialValueText("–")
        note = QPlainTextEdit()
        note.setMinimumHeight(60)
        name_edit = QLineEdit()
        self._name_edit = name_edit
        inv_btn = QPushButton("Aus Inventar …")
        inv_btn.setToolTip("Bezeichnung aus aktivem Vereinsinventar übernehmen")
        inv_btn.clicked.connect(self._pick_from_inventory)
        self.form.add("number", "Ziel-Nr.", num, required=True)
        self._inv_btn = inv_btn
        self.form.add("animal_name", "Tier / Bezeichnung", name_edit)
        self.form.add("distance_m", "Distanz", dist)
        self.form.add("arrow_stop_class", "Pfeilstoppklasse", arrow)
        self.form.add("terrain_type", "Geländetyp", terrain)
        self.form.add("max_group_size", "Max. Gruppengröße", grp)
        self.form.add_note(help_link("Parcours, Zeitplan & Preise", "auslosung"))
        self.form.add("helper_note", "Helfernotiz", note)

    def _pick_from_inventory(self):
        from bowtally.services import inventory_service as inv
        items = inv.list_items(course_only=True)
        if not items:
            Toast.show(self, "Kein Inventar für die Parcoursplanung vorhanden.", Toast.WARNING)
            return
        options = [(i.name, i.name) for i in items]
        result = choose(self, "Aus Inventar wählen", "Bezeichnung übernehmen:", options)
        if result is not choose.CANCELLED and result:
            self.form.set_values({"animal_name": result})

    def _do_save(self) -> bool:
        vals = self.form.values()
        data = {
            "number": int(vals["number"]),
            "animal_name": vals["animal_name"],
            "distance_m": float(vals["distance_m"]) or None,
            "arrow_stop_class": vals["arrow_stop_class"] or None,
            "terrain_type": vals["terrain_type"] or None,
            "max_group_size": int(vals["max_group_size"]) or None,
            "helper_note": vals["helper_note"],
        }
        try:
            t = cs.save_target(data, self._record.id if self._record else None,
                               context.tournament_id)
        except Exception as exc:
            show_error(self, exc, "Ziel konnte nicht gespeichert werden")
            return False
        self.saved_id = t.id
        return True


class CourseView(ListView):
    def __init__(self, parent=None):
        empty = EmptyState("target", "Noch keine Ziele",
                           "Lege Ziele an, um den Parcours zu planen.", "Neues Ziel")
        super().__init__("Parcours-Planung", HEADERS, empty,
                         search_placeholder="Tier, Pfeilstopp oder Gelände …",
                         reorderable=True, parent=parent)
        empty.actionTriggered.connect(self.new_item)
        self._btn_new = button("Neues Ziel", self.new_item, "primary",
                               "Neues Ziel anlegen (Strg+N)")
        self.header.add(self._btn_new,
                        button("Aufbauplan", self._print_setup, tooltip="Aufbauplan mit Helfernotizen als PDF"),
                        button("Zielplan", self._print_layout, tooltip="Zielplan ohne Notizen als PDF"))
        self.table.activated.connect(self.edit_item)
        self.table.reordered.connect(self._save_order)
        self._targets = {}

    def set_tournament(self, _t):
        self.refresh()

    def refresh(self):
        if not context.tournament_id:
            self.table.set_rows([], [])
            return
        rows = cs.list_targets(context.tournament_id)
        self._targets = {r.id: r for r in rows}
        self.table.set_rows([[
            r.number,
            r.animal_name or "",
            f"{r.distance_m:.1f}" if r.distance_m else "",
            r.arrow_stop_class or "",
            r.terrain_type or "",
            r.max_group_size or "",
            Cell(r.helper_note or "", tooltip=r.helper_note or ""),
        ] for r in rows], [r.id for r in rows])
        t = context.tournament()
        n = len(rows)
        self.header.set_subtitle(f"{n} Ziel{'e' if n != 1 else ''}"
                                 + (f" | Turnier: {t.name}" if t else ""))
        self.on_selection(self.table.selected_ids())

    def on_selection(self, ids):
        r = self._targets.get(self.table.selected_id())
        closed = self.tournament_closed
        self._btn_new.setEnabled(not closed)
        self.table.table.setDragEnabled(not closed)
        if r is None:
            self.action_bar.set_actions("", [])
            return
        self.action_bar.set_actions(
            f"Ziel {r.number}" + (f" – {r.animal_name}" if r.animal_name else ""),
            [Action("Bearbeiten", self.edit_item, enabled=not closed),
             Action("Löschen", self.delete_item, "danger", enabled=not closed)])

    def new_item(self):
        if not context.tournament_id or self.tournament_closed:
            return
        max_num = max((r.number for r in self._targets.values()), default=0)
        dlg = CourseTargetDialog(parent=self)
        dlg.form.set_values({"number": max_num + 1})
        dlg._baseline = dlg.form.snapshot()
        if dlg.exec():
            self.refresh()
            self.table.select_ids([dlg.saved_id])

    def edit_item(self):
        r = self._targets.get(self.table.selected_id())
        if r is None or self.tournament_closed:
            return
        dlg = CourseTargetDialog(r, parent=self)
        if dlg.exec():
            self.refresh()
            self.table.select_ids([dlg.saved_id])

    def delete_item(self):
        r = self._targets.get(self.table.selected_id())
        if r is None:
            return
        label = f"Ziel {r.number}" + (f" – {r.animal_name}" if r.animal_name else "")
        if not ConfirmDialog.ask(self, "Ziel löschen?", label + " wird gelöscht."):
            return
        try:
            cs.delete_target(r.id)
        except Exception as exc:
            show_error(self, exc, "Löschen fehlgeschlagen")
            return
        Toast.show(self, f"{label} gelöscht", Toast.SUCCESS)
        self.refresh()

    def context_entries(self, row_id):
        r = self._targets.get(row_id)
        if r is None:
            return []
        closed = self.tournament_closed
        return [("Bearbeiten", self.edit_item, not closed),
                None,
                ("Löschen", self.delete_item, not closed)]

    def _save_order(self, ordered_ids: list):
        if not context.tournament_id:
            return
        try:
            cs.reorder_targets(context.tournament_id, ordered_ids)
        except Exception as exc:
            show_error(self, exc, "Reihenfolge konnte nicht gespeichert werden")

    def _print_setup(self):
        self._print_pdf(with_notes=True)

    def _print_layout(self):
        self._print_pdf(with_notes=False)

    def _print_pdf(self, with_notes: bool):
        tid = context.tournament_id
        if not tid:
            return
        try:
            with busy():
                from bowtally.reports.course_plan import build_course_plan
                from bowtally.ui.dialogs.export_helper import open_path
                path = build_course_plan(tid, with_notes=with_notes)
            label = "Aufbauplan" if with_notes else "Zielplan"
            Toast.show(self, f"{label} erstellt", Toast.SUCCESS,
                       ("Öffnen", lambda: open_path(self, path)))
        except Exception as exc:
            show_error(self, exc, "PDF konnte nicht erstellt werden")


class CourseItemDialog(RecordDialog):
    """Material for the course plan: an inventory item or a one-off posting with a quantity."""
    _default_size = (680, 440)
    _size_name = "CourseItemDialog_v2"

    def __init__(self, record=None, one_off=False, parent=None):
        self._record = record
        self._one_off = record.is_one_off if record else one_off
        super().__init__("Einmalposten" if self._one_off else "Material aus Inventar", parent=parent)
        if record:
            self.form.set_values({"name": record.name, "unit_price": record.unit_price,
                                  "quantity": record.quantity,
                                  "inventory_item_id": record.inventory_item_id})
        self._baseline = self.form.snapshot()
        self.saved_id: int | None = None

    def _setup_form(self):
        quantity = QSpinBox()
        quantity.setRange(1, 9999)
        if self._one_off:
            self.form.add("name", "Bezeichnung", QLineEdit(), required=True)
            self.form.add("unit_price", "Einzelpreis", AmountField())
        else:
            combo = QComboBox()
            items = inv.list_items(course_only=True)
            current = self._record.inventory_item if self._record else None
            if current and current.id not in {i.id for i in items}:
                items.append(current)       # still shown after its planning flag was removed
            for item in items:
                combo.addItem(f"{item.name} (Bestand {item.quantity})", item.id)
            combo.setEnabled(self._record is None)      # to swap the article, remove and add again
            self.form.add("inventory_item_id", "Artikel", combo, required=True)
        self.form.add("quantity", "Angeforderte Menge", quantity)

    def _do_save(self) -> bool:
        vals = self.form.values()
        data = {"quantity": int(vals["quantity"])}
        data.update({"name": vals["name"], "unit_price": vals["unit_price"]} if self._one_off
                    else {"inventory_item_id": vals["inventory_item_id"]})
        try:
            item = cs.save_course_item(data, self._record.id if self._record else None,
                                       context.tournament_id)
        except Exception as exc:
            show_error(self, exc, "Posten konnte nicht gespeichert werden")
            return False
        self.saved_id = item.id
        return True


class CourseMaterialView(ListView):
    def __init__(self, parent=None):
        empty = EmptyState("target", "Noch kein Material",
                           "Wähle Artikel aus dem Inventar oder lege Einmalposten an.",
                           "Aus Inventar hinzufügen")
        super().__init__("Material", MATERIAL_HEADERS, empty,
                         search_placeholder="Artikel …", parent=parent)
        empty.actionTriggered.connect(self.new_item)
        self._btn_new = button("Aus Inventar hinzufügen", self.new_item, "primary",
                               "Artikel mit Parcoursplanung-Kennzeichen aus dem Inventar wählen (Strg+N)")
        self._btn_one_off = button("Einmalposten anlegen", self.new_one_off,
                                   tooltip="Material nur für dieses Turnier, nicht im Inventar")
        self.header.add(self._btn_new, self._btn_one_off)
        self.totals = QLabel()
        self.main_layout.insertWidget(2, self.totals)       # between table and action bar
        self.table.activated.connect(self.edit_item)
        self._items = {}

    def set_tournament(self, _t):
        self.refresh()

    def refresh(self):
        tid = context.tournament_id
        if not tid:
            self.table.set_rows([], [])
            return
        rows = cs.list_course_items(tid)
        self._items = {r.id: r for r in rows}
        self.table.set_rows([self._row(r) for r in rows], [r.id for r in rows])
        self.totals.setText(f"Kosten Einmalartikel: {money(cs.one_off_cost(tid))}   |   "
                            f"Warenwert Bestandsinventar: {money(cs.stock_goods_value(tid))}")
        t = context.tournament()
        self.header.set_subtitle(f"{len(rows)} Posten" + (f" | Turnier: {t.name}" if t else ""))
        self.on_selection(self.table.selected_ids())

    @staticmethod
    def _row(r) -> list:
        stock = r.inventory_item
        price = stock.unit_price if stock else r.unit_price
        colors = theme.current()
        if stock is None:
            status = Cell("–")
        elif (missing := cs.stock_shortfall(r)):
            status = Cell(f"Es fehlen {missing}", foreground=colors["danger"], bold=True)
        else:
            status = Cell("gedeckt", foreground=colors["success"])
        return [r.name, r.quantity, stock.quantity if stock else "–", status,
                Cell(price, text=money(price)), Cell(price * r.quantity, text=money(price * r.quantity)),
                "Einmalposten" if r.is_one_off else "Inventar"]

    def on_selection(self, ids):
        r = self._items.get(self.table.selected_id())
        closed = self.tournament_closed
        for btn in (self._btn_new, self._btn_one_off):
            btn.setEnabled(not closed)
        if r is None:
            self.action_bar.set_actions("", [])
            return
        self.action_bar.set_actions(r.name, [
            Action("Bearbeiten", self.edit_item, enabled=not closed),
            Action("Entfernen", self.delete_item, "danger", enabled=not closed)])

    def new_item(self):
        if not context.tournament_id or self.tournament_closed:
            return
        if not inv.list_items(course_only=True):
            Toast.show(self, "Kein Inventar für die Parcoursplanung vorhanden.", Toast.WARNING)
            return
        self._open(CourseItemDialog(parent=self))

    def new_one_off(self):
        if context.tournament_id and not self.tournament_closed:
            self._open(CourseItemDialog(one_off=True, parent=self))

    def edit_item(self):
        r = self._items.get(self.table.selected_id())
        if r is not None and not self.tournament_closed:
            self._open(CourseItemDialog(r, parent=self))

    def _open(self, dlg):
        if dlg.exec():
            self.refresh()
            self.table.select_ids([dlg.saved_id])

    def delete_item(self):
        r = self._items.get(self.table.selected_id())
        if r is None or not ConfirmDialog.ask(self, "Posten entfernen?",
                                              f"„{r.name}“ wird aus dem Parcoursplan entfernt.",
                                              "Entfernen"):
            return
        try:
            cs.delete_course_item(r.id)
        except Exception as exc:
            show_error(self, exc, "Entfernen fehlgeschlagen")
            return
        self.refresh()

    def context_entries(self, row_id):
        if row_id not in self._items:
            return []
        closed = self.tournament_closed
        return [("Bearbeiten", self.edit_item, not closed), None,
                ("Entfernen", self.delete_item, not closed)]


class CoursePage(QTabWidget):
    """Parcours tab of a tournament: targets and material side by side."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDocumentMode(True)
        self.addTab(CourseView(), "Ziele")
        self.addTab(CourseMaterialView(), "Material")

    def set_tournament(self, t):
        self.currentWidget().set_tournament(t)

    def shortcut_new(self):
        self.currentWidget().shortcut_new()

    def shortcut_find(self):
        self.currentWidget().shortcut_find()
