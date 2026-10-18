# -*- coding: utf-8 -*-
"""5-step tournament wizard (also used to edit an existing tournament).

Every page shows a horizontal step indicator, a title and a short explanation.
"""
from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (QAbstractItemView, QDateEdit, QFormLayout, QFrame, QGridLayout,
                               QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QPlainTextEdit, QPushButton, QScrollArea,
                               QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
                               QWizard, QWizardPage)

from bowtally.services import master_data_service as md
from bowtally.services import scoring_service as sc
from bowtally.services import tournament_service as ts
from bowtally.ui import button, repolish, show_error
from bowtally.ui.components.toast import Toast

DEFAULT_TARGETS = 28
STEPS = ["Grunddaten", "Regelwerk", "Bogenklassen", "Konfiguration", "Zusammenfassung"]
CHIP_COLUMNS = 3


class StepIndicator(QWidget):
    def __init__(self, current: int):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 12)
        lay.setSpacing(8)
        for i, name in enumerate(STEPS):
            state = "current" if i == current else "done" if i < current else "todo"
            dot = QLabel("✓" if state == "done" else str(i + 1), objectName="stepDot")
            dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label = QLabel(name, objectName="stepLabel")
            for w in (dot, label):
                w.setProperty("state", state)
                repolish(w)
            lay.addWidget(dot)
            lay.addWidget(label)
            if i < len(STEPS) - 1:
                line = QFrame(objectName="stepLine")
                line.setMinimumWidth(16)
                lay.addWidget(line, 1)


class _Page(QWizardPage):
    def __init__(self, step: int, title: str, explanation: str, is_complete=None):
        super().__init__()
        self._is_complete = is_complete
        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.addWidget(StepIndicator(step))
        outer.addWidget(QLabel(title, objectName="wizardTitle"))
        info = QLabel(explanation, objectName="pageSubtitle")
        info.setWordWrap(True)
        outer.addWidget(info)
        outer.addSpacing(8)
        self.body = QVBoxLayout()
        outer.addLayout(self.body, 1)

    def isComplete(self) -> bool:
        return self._is_complete() if self._is_complete else super().isComplete()


class TournamentWizard(QWizard):
    def __init__(self, tournament=None, parent=None):
        super().__init__(parent)
        self.tournament = tournament
        self.created_id: int | None = None
        self.setWindowTitle("Turnier bearbeiten" if tournament else "Neues Turnier")
        self.setWizardStyle(QWizard.WizardStyle.ClassicStyle)
        self.setOption(QWizard.WizardOption.NoBackButtonOnStartPage)
        self.resize(820, 640)
        self.setButtonText(QWizard.WizardButton.NextButton, "Weiter")
        self.setButtonText(QWizard.WizardButton.BackButton, "Zurück")
        self.setButtonText(QWizard.WizardButton.CancelButton, "Abbrechen")
        self.setButtonText(QWizard.WizardButton.FinishButton,
                           "Speichern" if tournament else "Turnier erstellen")
        for which in (QWizard.WizardButton.FinishButton, QWizard.WizardButton.NextButton):
            self.button(which).setProperty("primary", True)
            repolish(self.button(which))
        self.rules = sc.list_rules()
        self.classes = md.list_bow_classes()
        for page in (self._page_basics(), self._page_rule(), self._page_classes(),
                     self._page_config(), self._page_summary()):
            self.addPage(page)

    # ------------------------------------------------------------ 1 basics
    def _page_basics(self) -> QWizardPage:
        t = self.tournament
        self.name = QLineEdit(t.name if t else "")
        self.name.setPlaceholderText("z. B. 3D-Waldturnier 2026")
        self.date = QDateEdit()
        self.date.setDate(QDate(t.date) if t else QDate.currentDate())
        self.date.setCalendarPopup(True)
        self.date.setDisplayFormat("dd.MM.yyyy")
        self.location = QLineEdit(t.location or "" if t else "")
        self.organizer = QLineEdit(t.organizer or "" if t else "")
        self.description = QPlainTextEdit(t.description or "" if t else "")
        self.description.setFixedHeight(90)
        page = _Page(0, "Grunddaten", "Wie heißt das Turnier, wann und wo findet es statt? "
                     "Pflicht ist nur der Name.", lambda: bool(self.name.text().strip()))
        self.name.textChanged.connect(page.completeChanged)
        form = QFormLayout()
        form.addRow("Turniername *", self.name)
        form.addRow("Datum *", self.date)
        form.addRow("Ort", self.location)
        form.addRow("Veranstalter", self.organizer)
        form.addRow("Beschreibung", self.description)
        page.body.addLayout(form)
        page.body.addStretch()
        return page

    # ------------------------------------------------------------ 2 rule
    def _page_rule(self) -> QWizardPage:
        self.rule_list = QListWidget()
        for r in self.rules:
            item = QListWidgetItem(r.name + ("  ·  eingebaut" if r.is_builtin else ""))
            item.setData(Qt.ItemDataRole.UserRole, r.id)
            self.rule_list.addItem(item)
            if self.tournament and r.id == self.tournament.scoring_rule_id:
                self.rule_list.setCurrentItem(item)
        self.matrix = QTableWidget(0, 2)
        self.matrix.setHorizontalHeaderLabels(["Zone", "Punkte"])
        self.matrix.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.matrix.verticalHeader().hide()
        self.matrix.setShowGrid(False)
        self.matrix.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.matrix.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.rule_info = QLabel(objectName="pageSubtitle")
        self.rule_info.setWordWrap(True)
        page = _Page(1, "Regelwerk", "Nach welchem Regelwerk wird gewertet? Rechts siehst du "
                     "die Punkte je Trefferzone. Es gibt bewusst keine Vorauswahl.",
                     lambda: self.selected_rule() is not None)
        self.rule_list.currentItemChanged.connect(lambda *_: (self._show_rule(),
                                                              page.completeChanged.emit()))
        right = QVBoxLayout()
        right.addWidget(QLabel("Punktematrix", objectName="fieldLabel"))
        right.addWidget(self.matrix, 1)
        right.addWidget(self.rule_info)
        row = QHBoxLayout()
        row.addWidget(self.rule_list, 1)
        row.addLayout(right, 1)
        page.body.addLayout(row)
        self._show_rule()
        return page

    def selected_rule(self):
        item = self.rule_list.currentItem()
        if item is None:
            return None
        rid = item.data(Qt.ItemDataRole.UserRole)
        return next(r for r in self.rules if r.id == rid)

    def _show_rule(self):
        rule = self.selected_rule()
        zones = rule.ring_values if rule else []
        self.matrix.setRowCount(len(zones))
        for i, z in enumerate(zones):
            self.matrix.setItem(i, 0, QTableWidgetItem(z["zone"]))
            pts = QTableWidgetItem(str(z["points"]))
            pts.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.matrix.setItem(i, 1, pts)
        self.rule_info.setText(
            f"{rule.max_shots_per_target} Schuss je Scheibe"
            f"{', Nachschuss erlaubt' if rule.allow_retry_shot else ''}. "
            f"{(rule.rules_json or {}).get('note', '')}" if rule
            else "Bitte links ein Regelwerk auswählen.")
        if rule and hasattr(self, "shots"):
            self.shots.setMaximum(rule.max_shots_per_target)
            if not self.tournament:
                self.shots.setValue(rule.max_shots_per_target)

    # ------------------------------------------------------------ 3 classes (chips)
    def _page_classes(self) -> QWizardPage:
        selected = {bc.id for bc in self.tournament.bow_classes} if self.tournament else None
        self.class_chips: dict[int, QPushButton] = {}
        page = _Page(2, "Bogenklassen", "Welche Klassen werden gewertet? Zum An- und Abwählen "
                     "einfach anklicken. Eingebaute Klassen sind vorausgewählt.",
                     lambda: any(c.isChecked() for c in self.class_chips.values()))
        inner = QWidget()
        grid = QGridLayout(inner)
        grid.setSpacing(8)
        for i, bc in enumerate(self.classes):
            chip = QPushButton(f"{bc.name}  ({bc.abbreviation})" if bc.abbreviation else bc.name,
                               objectName="chip", checkable=True)
            chip.setChecked(bc.id in selected if selected is not None else bc.is_builtin)
            chip.setToolTip(bc.description or bc.name)
            chip.toggled.connect(page.completeChanged)
            self.class_chips[bc.id] = chip
            grid.addWidget(chip, i // CHIP_COLUMNS, i % CHIP_COLUMNS)
        grid.setRowStretch(len(self.classes) // CHIP_COLUMNS + 1, 1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(inner)
        tools = QHBoxLayout()
        tools.addWidget(button("Alle", lambda: self._set_all_classes(True),
                               tooltip="Alle Klassen auswählen"))
        tools.addWidget(button("Keine", lambda: self._set_all_classes(False),
                               tooltip="Auswahl aufheben"))
        tools.addStretch()
        page.body.addLayout(tools)
        page.body.addWidget(scroll, 1)
        return page

    def _set_all_classes(self, checked: bool):
        for chip in self.class_chips.values():
            chip.setChecked(checked)

    # ------------------------------------------------------------ 4 config
    def _page_config(self) -> QWizardPage:
        t = self.tournament
        self.targets = QSpinBox()
        self.targets.setRange(1, 200)
        self.targets.setValue(t.num_targets if t else DEFAULT_TARGETS)
        self.shots = QSpinBox()
        rule = self.selected_rule()
        self.shots.setRange(1, rule.max_shots_per_target if rule else 3)
        self.shots.setValue(t.shots_per_target if t else
                            rule.max_shots_per_target if rule else 1)
        self.groups = QLineEdit(t.start_groups or "" if t else "")
        self.groups.setPlaceholderText("z. B. A, B, C, D")
        page = _Page(3, "Konfiguration", "Wie viele Scheiben hat der Parcours und wie viele "
                     "Schüsse je Scheibe? Startgruppen sind optional und werden bei der "
                     "Startnummernvergabe reihum verteilt.")
        form = QFormLayout()
        form.addRow("Anzahl Scheiben", self.targets)
        form.addRow("Schüsse je Scheibe", self.shots)
        form.addRow("Startgruppen", self.groups)
        page.body.addLayout(form)
        page.body.addStretch()
        return page

    # ------------------------------------------------------------ 5 summary
    def _page_summary(self) -> QWizardPage:
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setTextFormat(Qt.TextFormat.RichText)
        self.summary.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.summary.linkActivated.connect(self._jump)
        page = _Page(4, "Zusammenfassung", "Bitte prüfen. Über „Bearbeiten“ springst du "
                     "direkt zum jeweiligen Schritt.")
        page.initializePage = self._fill_summary
        page.validatePage = self._create
        page.body.addWidget(self.summary, 1)
        return page

    def _jump(self, link: str):
        target = int(link)
        while self.currentId() > target:
            self.back()

    def _class_ids(self) -> list[int]:
        return [cid for cid, chip in self.class_chips.items() if chip.isChecked()]

    def _fill_summary(self):
        rule = self.selected_rule()
        names = [bc.name for bc in self.classes if bc.id in self._class_ids()]
        groups = ts.split_groups(self.groups.text())

        def esc(s):
            return str(s).replace("&", "&amp;").replace("<", "&lt;")

        sections = [
            (0, "Grunddaten", [("Name", self.name.text()),
                               ("Datum", self.date.date().toString("dd.MM.yyyy")),
                               ("Ort", self.location.text() or "–"),
                               ("Veranstalter", self.organizer.text() or "–")]),
            (1, "Regelwerk", [("Regelwerk", rule.name if rule else "–"),
                              ("Zonen", ", ".join(f"{z['zone']} {z['points']}"
                                                  for z in (rule.ring_values if rule else [])))]),
            (2, "Bogenklassen", [(f"{len(names)} Klassen", ", ".join(names))]),
            (3, "Konfiguration", [("Parcours", f"{self.targets.value()} Scheiben × "
                                               f"{self.shots.value()} Schuss"),
                                  ("Startgruppen", ", ".join(groups) or "keine")]),
        ]
        html = []
        for step, title, rows in sections:
            html.append(f"<p style='margin-top:10px'><b style='font-size:11pt'>{title}</b>"
                        f"&nbsp;&nbsp;<a href='{step}'>Bearbeiten</a></p><table cellpadding='3'>")
            html += [f"<tr><td style='padding-right:16px'>{k}</td><td>{esc(v)}</td></tr>"
                     for k, v in rows]
            html.append("</table>")
        self.summary.setText("".join(html))

    def _create(self) -> bool:
        data = {"name": self.name.text().strip(), "date": self.date.date().toPython(),
                "location": self.location.text().strip() or None,
                "organizer": self.organizer.text().strip() or None,
                "description": self.description.toPlainText().strip() or None,
                "scoring_rule_id": self.selected_rule().id,
                "num_targets": self.targets.value(), "shots_per_target": self.shots.value(),
                "start_groups": ", ".join(ts.split_groups(self.groups.text())) or None}
        try:
            t = ts.save_tournament(data, self._class_ids(),
                                   self.tournament.id if self.tournament else None)
        except Exception as exc:
            show_error(self, exc, "Turnier konnte nicht gespeichert werden")
            return False
        self.created_id = t.id
        Toast.show(self.parent() or self, f"Turnier '{t.name}' "
                   f"{'gespeichert' if self.tournament else 'erstellt'}", Toast.SUCCESS)
        return True
