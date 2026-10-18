# -*- coding: utf-8 -*-
"""Scoring rule editor with zone table (add / delete / move rows)."""
import json

from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QDialog, QDialogButtonBox,
                               QFormLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                               QPlainTextEdit, QSpinBox, QTableWidget, QTableWidgetItem,
                               QVBoxLayout)

from bowtally.services import ValidationError
from bowtally.services import scoring_service as sc
from bowtally.ui import button, show_error


class ScoringRuleDialog(QDialog):
    def __init__(self, rule=None, parent=None):
        super().__init__(parent)
        self.rule_id = rule.id if rule else None
        self.read_only = bool(rule and rule.is_builtin)
        self.setWindowTitle("Regelwerk" if rule else "Neues Regelwerk")
        self.resize(560, 620)

        self.name = QLineEdit(rule.name if rule else "")
        self.description = QPlainTextEdit(rule.description or "" if rule else "")
        self.description.setFixedHeight(60)
        self.max_shots = QSpinBox()
        self.max_shots.setRange(1, 10)
        self.max_shots.setValue(rule.max_shots_per_target if rule else 1)
        self.retry = QCheckBox("Wiederholungsschuss erlaubt")
        self.retry.setChecked(bool(rule and rule.allow_retry_shot))
        self.rules_json = QPlainTextEdit(json.dumps(rule.rules_json or {}, ensure_ascii=False,
                                                    indent=2) if rule else
                                         '{\n  "tiebreak": "most_top_scores"\n}')
        self.rules_json.setFixedHeight(90)

        self.zones = QTableWidget(0, 2)
        self.zones.setHorizontalHeaderLabels(["Zone", "Punkte"])
        self.zones.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.zones.verticalHeader().hide()
        self.zones.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.zones.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        for z in (rule.ring_values if rule else [{"zone": "Miss", "points": 0}]):
            self._add_zone(z["zone"], z["points"])

        zone_bar = QHBoxLayout()
        self.zone_buttons = [button("Zeile hinzufügen", lambda: self._add_zone("", 0)),
                             button("Zeile löschen", self._remove_zone, "danger"),
                             button("Nach oben", lambda: self._move(-1)),
                             button("Nach unten", lambda: self._move(1))]
        for b in self.zone_buttons:
            zone_bar.addWidget(b)
        zone_bar.addStretch()

        form = QFormLayout()
        form.addRow("Name *", self.name)
        form.addRow("Beschreibung", self.description)
        form.addRow("Max. Schüsse je Scheibe", self.max_shots)
        form.addRow("", self.retry)

        lay = QVBoxLayout(self)
        if self.read_only:
            hint = QLabel("Eingebautes Regelwerk – schreibgeschützt. Zum Anpassen klonen.")
            hint.setProperty("secondary", True)
            lay.addWidget(hint)
        lay.addLayout(form)
        lay.addWidget(QLabel("Zonen und Punktwerte"))
        lay.addWidget(self.zones, 1)
        lay.addLayout(zone_bar)
        lay.addWidget(QLabel("Sonderregeln (JSON)"))
        lay.addWidget(self.rules_json)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close if self.read_only else
                                   QDialogButtonBox.StandardButton.Save
                                   | QDialogButtonBox.StandardButton.Cancel)
        if not self.read_only:
            buttons.button(QDialogButtonBox.StandardButton.Save).setText("Speichern")
            buttons.button(QDialogButtonBox.StandardButton.Save).setProperty("primary", True)
            buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Abbrechen")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

        if self.read_only:
            for w in (self.name, self.description, self.rules_json):
                w.setReadOnly(True)
            self.max_shots.setEnabled(False)
            self.retry.setEnabled(False)
            self.zones.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            for b in self.zone_buttons:
                b.setEnabled(False)

    def _add_zone(self, zone: str, points: int):
        row = self.zones.rowCount()
        self.zones.insertRow(row)
        self.zones.setItem(row, 0, QTableWidgetItem(zone))
        self.zones.setItem(row, 1, QTableWidgetItem(str(points)))
        self.zones.setCurrentCell(row, 0)

    def _remove_zone(self):
        if self.zones.currentRow() >= 0:
            self.zones.removeRow(self.zones.currentRow())

    def _move(self, delta: int):
        row = self.zones.currentRow()
        target = row + delta
        if row < 0 or not 0 <= target < self.zones.rowCount():
            return
        values = [self.zones.item(row, c).text() for c in range(2)]
        self.zones.removeRow(row)
        self.zones.insertRow(target)
        for c, v in enumerate(values):
            self.zones.setItem(target, c, QTableWidgetItem(v))
        self.zones.setCurrentCell(target, 0)

    def _zones(self) -> list[dict]:
        out = []
        for r in range(self.zones.rowCount()):
            zone = (self.zones.item(r, 0).text() if self.zones.item(r, 0) else "").strip()
            pts = (self.zones.item(r, 1).text() if self.zones.item(r, 1) else "").strip()
            try:
                out.append({"zone": zone, "points": int(pts)})
            except ValueError:
                raise ValidationError(f"Zeile {r + 1}: Punktwert '{pts}' ist keine Zahl.") \
                    from None
        return out

    def _save(self):
        try:
            try:
                extra = json.loads(self.rules_json.toPlainText() or "{}")
            except json.JSONDecodeError as exc:
                raise ValidationError(f"Sonderregeln sind kein gültiges JSON: {exc}") from None
            if not isinstance(extra, dict):
                raise ValidationError("Sonderregeln müssen ein JSON-Objekt sein.")
            sc.save_rule({"name": self.name.text(),
                          "description": self.description.toPlainText().strip() or None,
                          "ring_values": self._zones(),
                          "max_shots_per_target": self.max_shots.value(),
                          "allow_retry_shot": self.retry.isChecked(),
                          "rules_json": extra}, self.rule_id)
        except Exception as exc:
            show_error(self, exc, "Regelwerk konnte nicht gespeichert werden")
            return
        self.accept()
