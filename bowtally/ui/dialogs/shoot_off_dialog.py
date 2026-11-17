# -*- coding: utf-8 -*-
"""Enter the shoot-off result of participants who are tied on places 1-3."""
from PySide6.QtWidgets import (QDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QSpinBox,
                               QVBoxLayout)

from bowtally.services import ranking_service as rs
from bowtally.services import scoring_service as sc
from bowtally.services import tournament_service as ts
from bowtally.ui import button, show_error


class ShootOffDialog(QDialog):
    def __init__(self, tournament_id: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Stechen eintragen")
        self.setMinimumWidth(460)
        self.spins: dict[int, QSpinBox] = {}
        stored = {p.id: p.shoot_off_points for p in ts.get_tournament(tournament_id).participants}
        lay = QVBoxLayout(self)
        groups = rs.podium_ties(tournament_id, include_resolved=True)
        lay.addWidget(QLabel(
            "Punkte des Stechens eintragen: Wer mehr hat, steht vorn. Bei gleichen Werten bleiben "
            "die Teilnehmer gleichauf (z. B. wenn das Stechen weitergeht). „–“ löscht den Wert."
            if groups else "Kein Gleichstand auf den Plätzen 1–3.", wordWrap=True))
        for group in groups:
            box = QGroupBox(f"{group.class_name} – Platz {group.rank}")
            form = QFormLayout(box)
            for row in group.rows:
                spin = QSpinBox()
                spin.setRange(-1, 999)
                spin.setSpecialValueText("–")
                spin.setValue(-1 if stored.get(row.participant_id) is None else stored[row.participant_id])
                self.spins[row.participant_id] = spin
                form.addRow(row.name, spin)
            lay.addWidget(box)
        buttons = QHBoxLayout()
        buttons.addStretch()
        save = button("Speichern", self.save, "primary")
        save.setEnabled(bool(groups))
        buttons.addWidget(save)
        buttons.addWidget(button("Abbrechen", self.reject))
        lay.addLayout(buttons)

    def save(self) -> bool:
        try:
            for participant_id, spin in self.spins.items():
                sc.set_shoot_off(participant_id, None if spin.value() == spin.minimum() else spin.value())
        except Exception as exc:
            show_error(self, exc, "Stechen konnte nicht gespeichert werden")
            return False
        self.accept()
        return True
