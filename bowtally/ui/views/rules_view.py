# -*- coding: utf-8 -*-
"""Scoring rules: modal CRUD with zone editor, clone, delete. Builtin rules are read-only."""
from PySide6.QtCore import QSettings, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QHeaderView, QHBoxLayout,
                               QLabel, QLineEdit, QPlainTextEdit, QSpinBox, QTabWidget,
                               QTableWidgetItem, QToolButton, QVBoxLayout, QWidget)

from bowtally.io.importer import RULE_IMPORT_FIELDS
from bowtally.services import scoring_service as sc
from bowtally.services import settings_service as ss
from bowtally.ui import busy, button, show_error, theme
from bowtally.ui.components.action_bar import Action
from bowtally.ui.components.confirm_dialog import ConfirmDialog
from bowtally.ui.components.data_table import (ROW_HEIGHT, Cell, ReorderTable, optional,
                                               optional_columns, optional_values)
from bowtally.ui.components.empty_state import EmptyState
from bowtally.ui.components.help_link import help_link
from bowtally.ui.components.markdown_edit import MarkdownEdit
from bowtally.ui.components.page_header import PageHeader
from bowtally.ui.components.toast import Toast
from bowtally.ui.context import context
from bowtally.reports.rules_pdf import build_rules_pdf
from bowtally.ui.dialogs.export_helper import export_button, open_path
from bowtally.ui.dialogs.import_dialog import run_import
from bowtally.ui.dialogs.record_dialog import RecordDialog
from bowtally.ui.views import ListView
from bowtally.ui.views.bow_classes_view import READ_ONLY_HINT, builtin_chip

HEADERS = ["Bezeichnung", "Zonen", "Schüsse/Scheibe", "Nachschuss", "Typ", "Standard"]
RULE_OPTIONAL = [
    (optional("description", "Beschreibung"), lambda r: r.description),
    (optional("created_at", "Angelegt am"), lambda r: r.created_at),
]
MAX_POINTS = 30
MAX_SHOTS = 3
ZONE_TYPES = sc.ZONE_TYPES


def zone_summary(rule) -> str:
    return " / ".join(f"{z['zone']} {z['points']}" for z in rule.ring_values)


class ZoneEditor(QWidget):
    """Zone / points rows: inline editing, delete per row, drag handle to reorder."""
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._zones: list[dict] = []
        self._read_only = False
        t = self.table = ReorderTable(0, 5)
        t.setHorizontalHeaderLabels(["", "Zone", "Punkte", "Typ", ""])
        t.verticalHeader().hide()
        t.verticalHeader().setDefaultSectionSize(ROW_HEIGHT + 6)
        t.setShowGrid(False)
        t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        t.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        t.setDragEnabled(True)
        t.setAcceptDrops(True)
        t.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        t.setDropIndicatorShown(True)
        h = t.horizontalHeader()
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for c, w in ((0, 30), (2, 80), (3, 110), (4, 40)):
            h.setSectionResizeMode(c, QHeaderView.ResizeMode.Fixed)
            t.setColumnWidth(c, w)
        t.setMinimumHeight(240)
        t.rowsDropped.connect(self._on_drop)
        self.add_btn = button("Zone hinzufügen", self._add, tooltip="Neue Trefferzone anlegen")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(t)
        lay.addWidget(self.add_btn, 0, Qt.AlignmentFlag.AlignLeft)

    # FormField protocol
    def field_value(self) -> list[dict]:
        return [dict(z) for z in self._zones]

    def set_field_value(self, zones) -> None:
        self._zones = [dict(z) for z in (zones or [])]
        self._rebuild()

    def setEnabled(self, enabled: bool) -> None:
        self._read_only = not enabled
        self.add_btn.setEnabled(enabled)
        self.table.setDragEnabled(enabled)
        self._rebuild()

    def _rebuild(self):
        t = self.table
        t.setRowCount(len(self._zones))
        muted = theme.current()["text2"]
        for r, z in enumerate(self._zones):
            grip = QTableWidgetItem()
            grip.setIcon(QIcon(theme.pixmap("grip", muted, 16)))
            grip.setToolTip("Ziehen, um die Reihenfolge zu ändern")
            grip.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
                          | Qt.ItemFlag.ItemIsDragEnabled)
            t.setItem(r, 0, grip)
            name = QLineEdit(z["zone"])
            name.setPlaceholderText("Zonenname")
            name.setReadOnly(self._read_only)
            name.textChanged.connect(lambda text, i=r: self._set(i, "zone", text))
            t.setCellWidget(r, 1, name)
            pts = QSpinBox()
            pts.setRange(0, MAX_POINTS)
            pts.setValue(int(z["points"]))
            pts.setEnabled(not self._read_only)
            pts.valueChanged.connect(lambda v, i=r: self._set(i, "points", v))
            t.setCellWidget(r, 2, pts)
            zone_type = QComboBox()
            for val, lbl in ZONE_TYPES:
                zone_type.addItem(lbl, val)
            cur_zt = z.get("type") or ""
            zone_type.setCurrentIndex(
                next((i for i, (v, _) in enumerate(ZONE_TYPES) if v == cur_zt), 0))
            zone_type.setEnabled(not self._read_only)
            zone_type.currentIndexChanged.connect(
                lambda _, i=r, cb=zone_type: self._set(i, "type", cb.currentData()))
            t.setCellWidget(r, 3, zone_type)
            delete = QToolButton(objectName="iconButton")
            delete.setIcon(QIcon(theme.pixmap("trash", theme.current()["accent"], 16)))
            delete.setToolTip("Zone löschen")
            delete.setEnabled(not self._read_only)
            delete.clicked.connect(lambda _=False, i=r: self._remove(i))
            t.setCellWidget(r, 4, delete)

    def _set(self, i, key, value):
        self._zones[i][key] = value.strip() if isinstance(value, str) else value
        self.changed.emit()

    def _add(self):
        self._zones.append({"zone": "", "points": 0, "type": ""})
        self._rebuild()
        self.table.cellWidget(len(self._zones) - 1, 1).setFocus()
        self.changed.emit()

    def _remove(self, i):
        del self._zones[i]
        self._rebuild()
        self.changed.emit()

    def _on_drop(self, rows: list, target: int):
        if self._read_only or not rows:
            return
        moving = self._zones.pop(rows[0])
        self._zones.insert(target if target <= rows[0] else target - 1, moving)
        self._rebuild()
        self.changed.emit()


def _zones_validator(zones) -> str | None:
    if not zones:
        return "Mindestens eine Zone ist erforderlich"
    names = [z["zone"].strip() for z in zones]
    if any(not n for n in names):
        return "Jede Zone braucht einen Namen"
    dup = {n for n in names if names.count(n) > 1}
    return f"Zone '{dup.pop()}' ist doppelt vorhanden" if dup else None


class ScoringRuleDialog(RecordDialog):
    _default_size = (956, 756)

    def __init__(self, record=None, parent=None):
        self._record = record
        ro = bool(record and record.is_builtin)
        super().__init__(
            "Neues Regelwerk" if record is None else "Regelwerk bearbeiten",
            read_only=ro, read_only_hint=READ_ONLY_HINT if ro else "", parent=parent)
        if record is None:
            self.form.set_values({"max_shots_per_target": 1, "discipline": "3d",
                                  "ring_values": [{"zone": "Miss", "points": 0}],
                                  "top_hits": True})
        else:
            discipline = sc.rule_discipline(record)
            specials = {sp["key"]: sp for sp in (record.tracked_specials or [])}
            values = {k: getattr(record, k) for k in self.form.fields if hasattr(record, k)}
            values["discipline"] = discipline
            for key in sc.COUNTER_KEYS:
                applies = sc.COUNTER_DISCIPLINE[key] == discipline
                values[f"count_{key}"] = applies and bool(specials.get(key, {}).get("track"))
                values[f"tie_{key}"] = applies and bool(specials.get(key, {}).get("tiebreak"))
            tiebreak = (record.rules_json or {}).get("tiebreak") or "most_top_scores"
            values["top_hits"] = tiebreak == "most_top_scores"
            values["top_first"] = bool((record.rules_json or {}).get("top_hits_first"))
            values["shoot_off"] = bool((record.rules_json or {}).get("shoot_off"))
            self.form.set_values(values)
        self._apply_discipline()
        self.form.fields["top_first"].widget.setEnabled(
            self.form.fields["top_hits"].widget.isChecked() and not ro)
        self._baseline = self.form.snapshot()
        self.saved_id: int | None = None
        self.saved_name: str = ""

    def _setup_form(self):
        desc = QPlainTextEdit()
        desc.setMinimumHeight(56)
        shots = QSpinBox()
        shots.setRange(1, MAX_SHOTS)
        ze = ZoneEditor()
        self.form.add("name", "Bezeichnung", QLineEdit(), required=True)
        self.form.add("description", "Beschreibung", desc)
        discipline = QComboBox()
        for key, label in sc.DISCIPLINES:
            discipline.addItem(label, key)
        self.form.add("discipline", "Disziplin", discipline)
        self.form.add("max_shots_per_target", "Max. Schüsse je Scheibe", shots)
        self.form.add("allow_retry_shot", "Nachschuss", QCheckBox("Nachschuss erlaubt"))
        self.form.add("ring_values", "Zonen", ze, required=True,
                      validator=_zones_validator,
                      required_message="Mindestens eine Zone ist erforderlich")
        self._add_counter_switches()

    def _add_counter_switches(self):
        """Kill / X: switch counting on, and whether the higher count wins a points tie."""
        f = self.form
        f.add_widget(QLabel("Zusatzwertungen und Gleichstand", objectName="sectionTitle"))
        for key, name in (("kill", "Kills"), ("x", "X-Treffer")):
            count = QCheckBox(f"{name} zählen")
            count.setToolTip("Nur bei 3D-Parcours" if key == "kill" else "Nur bei Scheibe")
            tie = QCheckBox(f"Bei gleicher Punktzahl gewinnt die höhere Anzahl an {name}")
            count.toggled.connect(lambda on, t=tie: t.setEnabled(on and not self._read_only))
            f.add(f"count_{key}", name, count)
            f.add(f"tie_{key}", "", tie)
        f.fields["discipline"].widget.currentIndexChanged.connect(lambda _i: self._apply_discipline())
        top_hits = QCheckBox("Bei Gleichstand gewinnt, wer mehr Treffer in der höchsten Wertung hat")
        top_first = QCheckBox("Diese Treffer vor Kills und X-Treffern prüfen")
        top_hits.toggled.connect(lambda on: top_first.setEnabled(on and not self._read_only))
        f.add("top_hits", "Treffer in der höchsten Wertung", top_hits)
        f.add("top_first", "", top_first)
        f.add("shoot_off", "Stechen", QCheckBox(
            "Bei Gleichstand auf Platz 1–3 ist ein Stechen erforderlich (zeigt einen Hinweis)"))
        f.add_note(help_link("Ergebnisse & Wertung", "gleichstand",
                             "Mehr dazu in der Hilfe: Gleichstand und Zusatzwertungen"))

    def _apply_discipline(self):
        """Kill is only available for 3D, X only for Scheibe; the other one is switched off."""
        fields = self.form.fields
        discipline = fields["discipline"].value()
        for key in sc.COUNTER_KEYS:
            count, tie = fields[f"count_{key}"].widget, fields[f"tie_{key}"].widget
            applies = sc.COUNTER_DISCIPLINE[key] == discipline and not self._read_only
            count.setEnabled(applies)
            if sc.COUNTER_DISCIPLINE[key] != discipline and not self._read_only:
                count.setChecked(False)
                tie.setChecked(False)
            tie.setEnabled(applies and count.isChecked())

    def _do_save(self) -> bool:
        data = self.form.values()
        discipline = data.pop("discipline")
        flags = {k: data.pop(k) for k in list(data)
                 if k.startswith(("count_", "tie_", "top_", "shoot_"))}
        data.update(sc.rule_options_to_data(
            discipline, flags, data["ring_values"],
            (self._record.tracked_specials or []) if self._record else None,
            self._record.rules_json if self._record else None))
        try:
            rule = sc.save_rule(data, self._record.id if self._record else None)
        except Exception as exc:
            show_error(self, exc, "Regelwerk konnte nicht gespeichert werden")
            return False
        self.saved_id = rule.id
        self.saved_name = rule.name
        return True


class _RulesTab(ListView):
    def __init__(self, parent=None):
        empty = EmptyState("rules", "Keine Regelwerke",
                           "Lege ein Regelwerk mit Zonen und Punktwerten an.", "Neues Regelwerk")
        super().__init__("Regelwerke", HEADERS + optional_columns(RULE_OPTIONAL), empty,
                         search_placeholder="Bezeichnung oder Zone …")
        empty.actionTriggered.connect(self.new_item)
        self.header.add(button("Neues Regelwerk", self.new_item, "primary",
                               "Neues Regelwerk anlegen (Strg+N)"))
        self.table.activated.connect(self.edit_item)
        self._rules = {}
        self._show_mine = QCheckBox("Meine Regelwerke anzeigen")
        _s = QSettings("BowTally", "BowTally")
        self._show_mine.setChecked(_s.value("rules/show_mine", False, type=bool))
        self._show_mine.toggled.connect(self.refresh)
        self._show_mine.toggled.connect(
            lambda v: QSettings("BowTally", "BowTally").setValue("rules/show_mine", v))
        _footer = QWidget()
        _fl = QHBoxLayout(_footer)
        _fl.setContentsMargins(0, 4, 0, 0)
        _fl.addWidget(self._show_mine)
        _fl.addStretch()
        _fl.addWidget(export_button(self, "regelwerke", self._export_sheets))
        _fl.addWidget(button("Importieren", self._import,
                             tooltip="Regelwerke aus CSV, Excel oder OpenDocument importieren"))
        self.main_layout.insertWidget(2, _footer)

    def refresh(self):
        rules = sc.list_rules()
        self._rules = {r.id: r for r in rules}
        default_id = ss.get("default_scoring_rule_id")
        visible = ([r for r in rules if not r.is_builtin]
                   if self._show_mine.isChecked() else rules)
        self.table.set_rows([[Cell(r.name, tooltip=READ_ONLY_HINT if r.is_builtin else ""),
                              zone_summary(r), r.max_shots_per_target, r.allow_retry_shot,
                              builtin_chip(r.is_builtin),
                              Cell("★", foreground=theme.GOLD) if default_id and str(r.id) == default_id else ""]
                             + optional_values(RULE_OPTIONAL, r) for r in visible],
                            [r.id for r in visible])
        custom = sum(not r.is_builtin for r in rules)
        self.header.set_subtitle(f"{len(rules)} Regelwerke | {custom} benutzerdefiniert")
        self.on_selection(self.table.selected_ids())

    def _selected(self):
        return self._rules.get(self.table.selected_id())

    def on_selection(self, ids):
        r = self._selected()
        if r is None:
            self.action_bar.set_actions("", [])
            return
        locked = r.is_builtin
        self.action_bar.set_actions(r.name, [
            Action("Bearbeiten", self.edit_item, enabled=not locked,
                   tooltip="Bearbeiten (Standard-Einträge sind schreibgeschützt)" if locked
                   else "Regelwerk bearbeiten"),
            Action("Kopieren", self.clone_item, tooltip="Anpassbare Kopie anlegen"),
            Action("Als Standard setzen", self._set_default, tooltip="Als Standard für neue Runden"),
            Action("Löschen", self.delete_item, "danger", enabled=not locked,
                   tooltip="Löschen (Standard-Einträge sind schreibgeschützt)" if locked
                   else "Regelwerk löschen (mit Rückfrage)")])

    def context_entries(self, row_id):
        r = self._rules.get(row_id)
        if r is None:
            return []
        return [("Bearbeiten", self.edit_item, not r.is_builtin),
                ("Kopieren", self.clone_item),
                ("Als Standard setzen", self._set_default),
                None,
                ("Löschen", self.delete_item, not r.is_builtin)]

    def _set_default(self):
        r = self._selected()
        if r is None:
            return
        ss.set_value("default_scoring_rule_id", str(r.id))
        Toast.show(self, f"'{r.name}' als Standard gesetzt", Toast.SUCCESS)
        self.refresh()

    def new_item(self):
        dlg = ScoringRuleDialog(parent=self)
        if dlg.exec() and dlg.saved_id:
            Toast.show(self, f"Regelwerk '{dlg.saved_name}' gespeichert", Toast.SUCCESS)
            self.refresh()
            self.table.select_ids([dlg.saved_id])

    def edit_item(self, *_):
        r = self._selected()
        if r is None:
            return
        dlg = ScoringRuleDialog(record=r, parent=self)
        if dlg.exec() and dlg.saved_id:
            Toast.show(self, f"Regelwerk '{dlg.saved_name}' gespeichert", Toast.SUCCESS)
            self.refresh()
            self.table.select_ids([dlg.saved_id])

    def clone_item(self):
        r = self._selected()
        if r is None:
            return
        clone = sc.clone_rule(r.id)
        Toast.show(self, f"Kopie '{clone.name}' angelegt", Toast.SUCCESS)
        self.refresh()
        self.table.select_ids([clone.id])
        self.edit_item()

    def delete_item(self):
        r = self._selected()
        if r is None or r.is_builtin:
            return
        if not ConfirmDialog.ask(self, "Regelwerk löschen?",
                                 f"'{r.name}' wird endgültig gelöscht."):
            return
        try:
            sc.delete_rule(r.id)
        except Exception as exc:
            show_error(self, exc)
            return
        Toast.show(self, f"Regelwerk '{r.name}' gelöscht", Toast.SUCCESS)
        self.refresh()

    def _export_sheets(self, _filtered: bool):
        return [("Regelwerke", sc.RULE_EXPORT_HEADERS,
                 [sc.rule_export_row(r) for r in self._rules.values()])]

    def _import(self):
        res = run_import(self, RULE_IMPORT_FIELDS, "Regelwerke importieren")
        if res is None:
            return
        records, strategy = res
        try:
            with busy():
                r = sc.import_rules(records, strategy)
        except Exception as exc:
            show_error(self, exc, "Import fehlgeschlagen")
            return
        Toast.show(self, f"Import abgeschlossen: {r['created']} neu, {r['updated']} "
                         f"aktualisiert, {r['skipped']} übersprungen", Toast.SUCCESS)
        self.refresh()


class _TournamentRulesTab(QWidget):
    """Globale Texte für den Turnierregeln-Aushang und die Ausschreibung (Einstellungen)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.header = PageHeader("Turnierregeln", "Gelten für alle Turniere")
        self._save_btn = button("Speichern", self._save, "primary", "Turnierregeln speichern")
        self.header.add(button("Turnierregeln exportieren", self._export_pdf,
                               tooltip="Druckbare PDF der Turnierregeln erstellen"), self._save_btn)
        self._rules = MarkdownEdit()
        self._terms = MarkdownEdit()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.header)
        for label, edit in (("Allgemeine Turnierregeln", self._rules),
                            ("Teilnahmebedingungen", self._terms)):
            lay.addWidget(QLabel(label))
            lay.addWidget(edit, 1)
            edit.textChanged.connect(self._update_save_state)
        self._load()

    def _texts(self) -> tuple[str, str]:
        return self._rules.toPlainText(), self._terms.toPlainText()

    def _load(self):
        self._saved = (ss.get(ss.KEY_TOURNAMENT_RULES_TEXT, ""), ss.get(ss.KEY_PARTICIPATION_TERMS_TEXT, ""))
        self._rules.setPlainText(self._saved[0])
        self._terms.setPlainText(self._saved[1])
        self._update_save_state()

    def _update_save_state(self):
        self._save_btn.setEnabled(self._texts() != self._saved)

    def _save(self):
        rules, terms = self._texts()
        ss.set_many({ss.KEY_TOURNAMENT_RULES_TEXT: rules, ss.KEY_PARTICIPATION_TERMS_TEXT: terms})
        self._saved = (rules, terms)
        self._update_save_state()
        Toast.show(self, "Turnierregeln gespeichert", Toast.SUCCESS)

    def _export_pdf(self):
        try:
            with busy():
                path = build_rules_pdf(context.tournament_id)
        except Exception as exc:
            show_error(self, exc, "Turnierregel-PDF konnte nicht erstellt werden")
            return
        Toast.show(self, "Turnierregeln exportiert", Toast.SUCCESS,
                   ("Öffnen", lambda: open_path(self, path)))

    def showEvent(self, e):
        super().showEvent(e)
        if self._texts() == self._saved:   # ungespeicherte Eingaben nicht überschreiben
            self._load()


class RulesView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tab_rules = _RulesTab()
        tabs = QTabWidget()
        tabs.addTab(self._tab_rules, "Regelwerke")
        tabs.addTab(_TournamentRulesTab(), "Turnierregeln")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(tabs)

    def shortcut_new(self):
        self._tab_rules.new_item()
