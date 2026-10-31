# -*- coding: utf-8 -*-
"""Auslosungs-Dialog: konfiguriert die Startgruppenauslosung und startet sie."""
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QHBoxLayout, QLabel,
                               QSpinBox, QVBoxLayout)

from bowtally.services import draw_service, score_sheet_service as sss
from bowtally.services import tournament_service as ts
from bowtally.ui import busy, button, show_error
from bowtally.ui.components.confirm_dialog import ConfirmDialog
from bowtally.ui.components.toast import Toast
from bowtally.ui.context import context


class DrawDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Auslosung")
        self.resize(460, 360)
        t = context.tournament()
        active = [p for p in (t.participants if t else [])
                  if ts.is_active_participant(p)]

        info = QLabel(f"Turnier: {t.name if t else '–'}")
        info.setObjectName("pageSubtitle")
        count_lbl = QLabel(f"{len(active)} aktive Teilnehmer")

        # --- Gruppengroesse
        grp_lay = QHBoxLayout()
        grp_lay.addWidget(QLabel("Teilnehmer pro Gruppe:"))
        self._grp_spin = QSpinBox()
        self._grp_spin.setRange(1, 20)
        self._grp_spin.setValue(4)
        self._grp_spin.valueChanged.connect(self._update_preview)
        grp_lay.addWidget(self._grp_spin)
        grp_lay.addStretch()

        # --- Rotation
        rot_lay = QHBoxLayout()
        rot_lay.addWidget(QLabel("Startscheiben-Zuweisung:"))
        self._rot_combo = QComboBox()
        self._rot_combo.addItem("Fortlaufend (Gruppe A → 1, B → 2 …)", "sequential")
        self._rot_combo.addItem("Zufällig (jede Gruppe bekommt zufällige Startscheibe)", "random")
        rot_lay.addWidget(self._rot_combo, 1)

        # --- Klassentrennung
        self._class_chk = QCheckBox("Klassen getrennt auslosen")

        # --- Wertungszettel
        self._sheet_combo = QComboBox()
        self._sheet_combo.addItem("Keinen (nur Auslosung)", None)
        for tmpl in sss.list_templates():
            self._sheet_combo.addItem(tmpl.name, tmpl.id)
        sheet_lay = QHBoxLayout()
        sheet_lay.addWidget(QLabel("Wertungszettel-Vorlage:"))
        sheet_lay.addWidget(self._sheet_combo, 1)

        # --- Vorschau
        self._preview_lbl = QLabel()
        self._preview_lbl.setObjectName("pageSubtitle")
        self._preview_lbl.setWordWrap(True)
        self._update_preview()

        hint = QLabel("Die bestehenden Startgruppen und -nummern werden überschrieben.")
        hint.setWordWrap(True)
        hint.setObjectName("readOnlyHint")

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(button("Abbrechen", self.reject))
        self._draw_btn = button("Auslosen", self._do_draw, "primary")
        btn_row.addWidget(self._draw_btn)

        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        lay.addWidget(info)
        lay.addWidget(count_lbl)
        lay.addLayout(grp_lay)
        lay.addLayout(rot_lay)
        lay.addWidget(self._class_chk)
        lay.addLayout(sheet_lay)
        lay.addWidget(self._preview_lbl)
        lay.addStretch()
        lay.addWidget(hint)
        lay.addLayout(btn_row)

    def _update_preview(self):
        t = context.tournament()
        if not t:
            return
        active = sum(1 for p in t.participants if ts.is_active_participant(p))
        size = self._grp_spin.value()
        import math
        groups = math.ceil(active / size) if size else 0
        self._preview_lbl.setText(
            f"Ergibt ca. {groups} Gruppe{'n' if groups != 1 else ''} "
            f"mit je {size} Teilnehmer{'n' if size != 1 else ''}.")

    def _do_draw(self):
        tid = context.tournament_id
        if not tid:
            return
        if not ConfirmDialog.ask(self, "Auslosung starten?",
                                 "Die bestehenden Startgruppen werden überschrieben.",
                                 "Auslosen"):
            return
        try:
            with busy():
                n = draw_service.draw_groups(
                    tid,
                    group_size=self._grp_spin.value(),
                    rotation=self._rot_combo.currentData(),
                    class_separated=self._class_chk.isChecked(),
                )
            from bowtally.ui.context import context as ctx
            ctx.notify()
            Toast.show(self.parent() or self, f"Auslosung abgeschlossen: {n} Teilnehmer zugeteilt",
                       Toast.SUCCESS)
            template_id = self._sheet_combo.currentData()
            if template_id:
                self._generate_sheets(tid, template_id)
            self.accept()
        except Exception as exc:
            show_error(self, exc, "Auslosung fehlgeschlagen")

    def _generate_sheets(self, tournament_id: int, template_id: int):
        try:
            with busy():
                from bowtally.reports.score_sheet import build_score_sheets
                from bowtally.ui.dialogs.export_helper import open_path
                path = build_score_sheets(tournament_id, template_id)
            Toast.show(self.parent() or self, "Wertungszettel erstellt", Toast.SUCCESS,
                       ("Öffnen", lambda: open_path(self.parent() or self, path)))
        except Exception as exc:
            show_error(self, exc, "Wertungszettel konnten nicht erstellt werden")
