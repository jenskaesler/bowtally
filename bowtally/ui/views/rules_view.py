# -*- coding: utf-8 -*-
"""Scoring rules: list, CRUD, clone. Builtin rules are read-only."""
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from bowtally.services import scoring_service as sc
from bowtally.ui import button, confirm, show_error
from bowtally.ui.dialogs.scoring_rule_dialog import ScoringRuleDialog
from bowtally.ui.views import page_title
from bowtally.ui.widgets.sortable_table import SortableTable

HEADERS = ["Name", "Zonen", "Schüsse/Scheibe", "Wiederholung", "Eingebaut", "Beschreibung"]


def zone_summary(rule) -> str:
    return " / ".join(f"{z['zone']} {z['points']}" for z in rule.ring_values)


class RulesView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.table = SortableTable(HEADERS)
        self.table.activated.connect(lambda _id: self._edit())
        bar = QHBoxLayout()
        bar.addWidget(button("Neu", self._new, "primary"))
        bar.addWidget(button("Bearbeiten", self._edit))
        bar.addWidget(button("Klonen", self._clone))
        bar.addWidget(button("Löschen", self._delete, "danger"))
        bar.addStretch()
        lay = QVBoxLayout(self)
        lay.addWidget(page_title("Regelwerke"))
        lay.addLayout(bar)
        lay.addWidget(self.table, 1)
        self._rules = {}

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()

    def refresh(self):
        rules = sc.list_rules()
        self._rules = {r.id: r for r in rules}
        self.table.set_rows([[r.name, zone_summary(r), r.max_shots_per_target,
                              r.allow_retry_shot, r.is_builtin, r.description] for r in rules],
                            [r.id for r in rules])

    def _selected(self):
        return self._rules.get(self.table.selected_id())

    def _new(self):
        if ScoringRuleDialog(parent=self).exec():
            self.refresh()

    def _edit(self):
        r = self._selected()
        if r and ScoringRuleDialog(r, self).exec():
            self.refresh()

    def _clone(self):
        r = self._selected()
        if r is None:
            return
        clone = sc.clone_rule(r.id)
        self.refresh()
        if ScoringRuleDialog(clone, self).exec():
            self.refresh()

    def _delete(self):
        r = self._selected()
        if r is None or not confirm(self, f"Regelwerk '{r.name}' löschen?"):
            return
        try:
            sc.delete_rule(r.id)
        except Exception as exc:
            show_error(self, exc)
        self.refresh()
