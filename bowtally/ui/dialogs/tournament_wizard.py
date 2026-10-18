# -*- coding: utf-8 -*-
"""5-step tournament wizard (also used to edit an existing tournament)."""
from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QDateEdit, QFormLayout, QHBoxLayout,
                               QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QPlainTextEdit, QScrollArea, QSpinBox, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget, QWizard, QWizardPage)

from bowtally.services import master_data_service as md
from bowtally.services import scoring_service as sc
from bowtally.services import tournament_service as ts
from bowtally.ui import show_error

DEFAULT_TARGETS = 28


class _Page(QWizardPage):
    def __init__(self, title: str, subtitle: str, is_complete=None):
        super().__init__()
        self.setTitle(title)
        self.setSubTitle(subtitle)
        self._is_complete = is_complete

    def isComplete(self) -> bool:
        return self._is_complete() if self._is_complete else super().isComplete()


class TournamentWizard(QWizard):
    def __init__(self, tournament=None, parent=None):
        super().__init__(parent)
        self.tournament = tournament
        self.created_id: int | None = None
        self.setWindowTitle("Turnier bearbeiten" if tournament else "Neues Turnier")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.resize(760, 600)
        self.setButtonText(QWizard.WizardButton.NextButton, "Weiter >")
        self.setButtonText(QWizard.WizardButton.BackButton, "< Zurück")
        self.setButtonText(QWizard.WizardButton.CancelButton, "Abbrechen")
        self.setButtonText(QWizard.WizardButton.FinishButton,
                           "Speichern" if tournament else "Erstellen")
        self.rules = sc.list_rules()
        self.classes = md.list_bow_classes()
        for page in (self._page_basics(), self._page_rule(), self._page_classes(),
                     self._page_config(), self._page_summary()):
            self.addPage(page)

    # ------------------------------------------------------------ page 1
    def _page_basics(self) -> QWizardPage:
        t = self.tournament
        self.name = QLineEdit(t.name if t else "")
        self.date = QDateEdit(QDate(t.date) if t else QDate.currentDate())
        self.date.setCalendarPopup(True)
        self.date.setDisplayFormat("dd.MM.yyyy")
        self.location = QLineEdit(t.location or "" if t else "")
        self.organizer = QLineEdit(t.organizer or "" if t else "")
        self.description = QPlainTextEdit(t.description or "" if t else "")
        page = _Page("Grunddaten", "Name, Datum und Ort des Turniers.",
                     lambda: bool(self.name.text().strip()))
        self.name.textChanged.connect(page.completeChanged)
        form = QFormLayout(page)
        form.addRow("Turniername *", self.name)
        form.addRow("Datum *", self.date)
        form.addRow("Ort", self.location)
        form.addRow("Veranstalter", self.organizer)
        form.addRow("Beschreibung", self.description)
        return page

    # ------------------------------------------------------------ page 2
    def _page_rule(self) -> QWizardPage:
        self.rule_list = QListWidget()
        for r in self.rules:
            item = QListWidgetItem(r.name + ("  (eingebaut)" if r.is_builtin else ""))
            item.setData(Qt.ItemDataRole.UserRole, r.id)
            self.rule_list.addItem(item)
            if self.tournament and r.id == self.tournament.scoring_rule_id:
                self.rule_list.setCurrentItem(item)
        self.matrix = QTableWidget(0, 2)
        self.matrix.setHorizontalHeaderLabels(["Zone", "Punkte"])
        self.matrix.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.matrix.verticalHeader().hide()
        self.matrix.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.rule_info = QLabel()
        self.rule_info.setWordWrap(True)
        self.rule_info.setProperty("secondary", True)

        page = _Page("Regelwerk", "Wertungsregelwerk auswählen (keine Vorauswahl).",
                     lambda: self.selected_rule() is not None)
        self.rule_list.currentItemChanged.connect(lambda *_: (self._show_rule(),
                                                              page.completeChanged.emit()))
        right = QVBoxLayout()
        right.addWidget(QLabel("Punktematrix"))
        right.addWidget(self.matrix)
        right.addWidget(self.rule_info)
        lay = QHBoxLayout(page)
        lay.addWidget(self.rule_list, 1)
        lay.addLayout(right, 1)
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
            self.matrix.setItem(i, 1, QTableWidgetItem(str(z["points"])))
        self.rule_info.setText(
            f"{rule.max_shots_per_target} Schuss je Scheibe"
            f"{', Wiederholungsschuss erlaubt' if rule.allow_retry_shot else ''}. "
            f"{(rule.rules_json or {}).get('note', '')}" if rule else "")
        if rule and hasattr(self, "shots") and not self.tournament:
            self.shots.setValue(rule.max_shots_per_target)

    # ------------------------------------------------------------ page 3
    def _page_classes(self) -> QWizardPage:
        selected = {bc.id for bc in self.tournament.bow_classes} if self.tournament else None
        self.class_checks: dict[int, QCheckBox] = {}
        inner = QWidget()
        lay = QVBoxLayout(inner)
        page = _Page("Bogenklassen", "Welche Klassen werden gewertet?",
                     lambda: any(c.isChecked() for c in self.class_checks.values()))
        for bc in self.classes:
            cb = QCheckBox(f"{bc.name} ({bc.abbreviation})" if bc.abbreviation else bc.name)
            cb.setChecked(bc.id in selected if selected is not None else bc.is_builtin)
            cb.toggled.connect(page.completeChanged)
            self.class_checks[bc.id] = cb
            lay.addWidget(cb)
        lay.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(inner)
        QVBoxLayout(page).addWidget(scroll)
        return page

    # ------------------------------------------------------------ page 4
    def _page_config(self) -> QWizardPage:
        t = self.tournament
        self.targets = QSpinBox()
        self.targets.setRange(1, 200)
        self.targets.setValue(t.num_targets if t else DEFAULT_TARGETS)
        self.shots = QSpinBox()
        self.shots.setRange(1, 10)
        rule = self.selected_rule()
        self.shots.setValue(t.shots_per_target if t else
                            rule.max_shots_per_target if rule else 1)
        self.groups = QLineEdit(t.start_groups or "" if t else "")
        self.groups.setPlaceholderText("z. B. A, B, C, D (leer = keine Startgruppen)")
        page = _Page("Konfiguration", "Parcours und Startgruppen.")
        form = QFormLayout(page)
        form.addRow("Anzahl Scheiben", self.targets)
        form.addRow("Schüsse je Scheibe", self.shots)
        form.addRow("Startgruppen", self.groups)
        return page

    # ------------------------------------------------------------ page 5
    def _page_summary(self) -> QWizardPage:
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setTextFormat(Qt.TextFormat.RichText)
        self.summary.setAlignment(Qt.AlignmentFlag.AlignTop)
        page = _Page("Zusammenfassung", "Bitte prüfen und anschließend speichern.")
        page.initializePage = self._fill_summary
        page.validatePage = self._create
        QVBoxLayout(page).addWidget(self.summary)
        return page

    def _class_ids(self) -> list[int]:
        return [cid for cid, cb in self.class_checks.items() if cb.isChecked()]

    def _fill_summary(self):
        rule = self.selected_rule()
        names = [bc.name for bc in self.classes if bc.id in self._class_ids()]
        groups = ts.split_groups(self.groups.text())
        rows = [("Name", self.name.text()), ("Datum", self.date.date().toString("dd.MM.yyyy")),
                ("Ort", self.location.text() or "-"),
                ("Veranstalter", self.organizer.text() or "-"),
                ("Regelwerk", rule.name if rule else "-"),
                ("Bogenklassen", ", ".join(names)),
                ("Scheiben", f"{self.targets.value()} × {self.shots.value()} Schuss"),
                ("Startgruppen", ", ".join(groups) or "keine")]
        esc = lambda s: str(s).replace("&", "&amp;").replace("<", "&lt;")  # noqa: E731
        self.summary.setText("<table cellpadding='4'>" + "".join(
            f"<tr><td><b>{k}</b></td><td>{esc(v)}</td></tr>" for k, v in rows) + "</table>")

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
        return True
