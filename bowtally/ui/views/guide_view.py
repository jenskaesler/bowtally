# -*- coding: utf-8 -*-
"""Guide (Leitfaden): what to do in the current phase of the active tournament.

Per phase: description, traffic lights for the next transition, status checks, tasks with
direct links, manually ticked checklist items and phase specific figures.
"""
from dataclasses import dataclass

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QCheckBox, QFrame, QGridLayout, QHBoxLayout, QLabel,
                               QPlainTextEdit, QScrollArea, QVBoxLayout, QWidget)

from bowtally.services import tournament_service as ts
from bowtally.ui import button, repolish
from bowtally.ui.components.capacity_bar import CapacityBar, ProgressBar
from bowtally.ui.components.page_header import PageHeader
from bowtally.ui.components.status_chip import StatusChip
from bowtally.ui.components.toast import Toast
from bowtally.ui.context import context


@dataclass
class Task:
    text: str
    link: str | None = None          # action key handled by the main window
    link_text: str = ""
    auto: str | None = None          # key of ts.get_status_checks -> done when ok
    manual: str | None = None        # key of ts.CHECKLIST_ITEMS -> done when ticked


PHASE_TASKS = {
    "draft": [
        Task("Turnierdaten eingeben", "edit", "Grunddaten bearbeiten"),
        Task("Bogenklassen festlegen", "edit_classes", "Bogenklassen bearbeiten"),
        Task("Startgebühren anlegen", "fees", "Startgebühren"),
        Task("Wenn alles bereit ist: in die Ausschreibungs-Phase wechseln"),
    ],
    "announcement": [
        Task("Turnierdaten prüfen", "edit", "Grunddaten bearbeiten"),
        Task("Kontaktdaten hinterlegen", "edit_contact", "Kontaktdaten eingeben", auto="contact"),
        Task("Bankdaten eintragen", "edit_bank", "Bankdaten eingeben", auto="bank"),
        Task("Startgebühren festlegen", "fees", "Startgebühren", auto="fees"),
        Task("Ausschreibungs-PDF generieren", "announcement", "PDF generieren",
             auto="announcement_current"),
        Task("Ausschreibung versenden (E-Mail, Aushang, Website)"),
    ],
    "preparation": [
        Task("Bogenklassen im Turnier prüfen", "edit_classes", "Bogenklassen bearbeiten"),
        Task("Parcours planen und aufbauen", manual="parcours_ready"),
        Task("Helfer einteilen (Notizen unten)", manual="helpers_assigned"),
        Task("Anmeldeliste vorbereiten", "participants", "Teilnehmerverwaltung"),
    ],
    "registration": [
        Task("Anmeldungen erfassen", "participants", "Teilnehmerverwaltung",
             auto="participants"),
        Task("Anmeldungen bestätigen", "participants", "Teilnehmerverwaltung",
             auto="all_confirmed"),
        Task("Zahlungseingang prüfen und bestätigen", "revenue", "Einnahmen-Übersicht",
             auto="all_paid"),
    ],
    "checkin": [
        Task("Einschreibeliste drucken", "print_checkin", "Teilnehmerliste drucken"),
        Task("Einschreibetisch vorbereiten", manual="checkin_desk_ready"),
        Task("Teilnehmer vor Ort einchecken", "checkin", "Einschreibe-Ansicht",
             auto="checkin_started"),
    ],
    "shooting": [
        Task("Parcours freigeben"),
        Task("Ergebnisse eingeben", "scoring", "Ergebniseingabe", auto="results_complete"),
    ],
    "scoring": [
        Task("Vollständigkeit prüfen", "scoring_incomplete", "Unvollständige anzeigen",
             auto="results_complete"),
        Task("Ergebnisliste generieren", "results_pdf", "Ergebnisliste generieren",
             auto="results_generated"),
        Task("Siegerehrung vorbereiten", manual="ceremony_ready"),
        Task("Ergebnisliste aushängen / versenden", "results", "Auswertung",
             manual="results_published"),
    ],
    "closed": [
        Task("Turnierdaten sichern", "export_all", "Alle Turnierdaten exportieren"),
    ],
}
PHASE_CHECKS = {
    "draft": [],
    "announcement": ["contact", "bank", "fees", "announced", "announcement_current"],
    "preparation": ["fees", "announcement_current"],
    "registration": ["participants", "all_confirmed", "all_paid"],
    "checkin": ["checkin_started", "all_paid"],
    "shooting": ["results_complete"],
    "scoring": ["results_complete", "results_generated", "all_paid"],
    "closed": [],
}
DEBRIEF_KEY = "debrief_notes"


def task_done(task: Task, checks: dict, checklist: dict) -> bool | None:
    """True / False, or None for purely informational tasks."""
    if task.auto:
        return checks[task.auto].ok
    if task.manual:
        return bool(checklist.get(task.manual))
    return None


def next_open_task(tournament_id: int) -> Task | None:
    t = ts.get_tournament(tournament_id)
    checks, checklist = ts.get_status_checks(tournament_id), ts.get_checklist_state(tournament_id)
    for task in PHASE_TASKS.get(t.phase, []):
        if task_done(task, checks, checklist) is False:
            return task
    return None


def _card(title: str) -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame(objectName="card")
    lay = QVBoxLayout(frame)
    lay.setContentsMargins(18, 14, 18, 16)
    lay.setSpacing(8)
    lay.addWidget(QLabel(title, objectName="sectionTitle"))
    return frame, lay


def _ampel(state: str) -> QLabel:
    dot = QLabel(objectName="ampel")
    dot.setProperty("state", state)
    repolish(dot)
    return dot


class GuideView(QWidget):
    action = Signal(str)          # direct link key, handled by the main window

    def __init__(self, parent=None):
        super().__init__(parent)
        self.header = PageHeader("Leitfaden")
        self.chip = StatusChip()
        self.header.add_title_widget(self.chip)
        self.body = QWidget()
        self.body_lay = QVBoxLayout(self.body)
        self.body_lay.setContentsMargins(0, 0, 8, 0)
        self.body_lay.setSpacing(14)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(self.body)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.header)
        lay.addWidget(scroll, 1)
        context.dataChanged.connect(self._refresh_if_visible)

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()

    def _refresh_if_visible(self):
        if self.isVisible():
            self.refresh()

    # ------------------------------------------------------------ build
    def refresh(self):
        while self.body_lay.count():
            item = self.body_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        t = context.tournament()
        if t is None:
            self.header.set_title("Leitfaden")
            self.header.set_subtitle("Kein Turnier geöffnet.")
            return
        self.tid = t.id
        idx = ts.phase_index(t.phase)
        self.header.set_title(f"Leitfaden: {ts.PHASE_LABELS[t.phase]}")
        self.header.set_subtitle(f"{t.name} · Phase {idx + 1} von {len(ts.PHASES)}")
        self.chip.set_tournament_status(t.phase)
        checks = ts.get_status_checks(t.id)
        checklist = ts.get_checklist_state(t.id)

        intro, lay = _card("Worum geht es in dieser Phase?")
        text = QLabel(ts.PHASE_DESCRIPTIONS.get(t.phase, ""))
        text.setWordWrap(True)
        lay.addWidget(text)
        self.body_lay.addWidget(intro)

        row = QHBoxLayout()
        row.setSpacing(14)
        row.addWidget(self._tasks_card(t, checks, checklist), 3)
        side = QVBoxLayout()
        side.setSpacing(14)
        nxt = ts.next_phase(t.phase)
        if nxt:
            side.addWidget(self._conditions_card(t, nxt))
        if PHASE_CHECKS.get(t.phase):
            side.addWidget(self._checks_card(t, checks))
        side.addStretch()
        row.addLayout(side, 2)
        self.body_lay.addLayout(row)
        extra = self._phase_card(t, checklist)
        if extra is not None:
            self.body_lay.addWidget(extra)
        self.body_lay.addStretch()

    def _tasks_card(self, t, checks, checklist) -> QFrame:
        card, lay = _card("Aufgaben")
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)
        locked = t.status == "closed" and t.phase != "closed"
        for r, task in enumerate(PHASE_TASKS.get(t.phase, [])):
            done = task_done(task, checks, checklist)
            if task.manual:
                box = QCheckBox(task.text)
                box.setChecked(bool(done))
                box.setEnabled(not locked)
                box.setToolTip("Manuell abhaken")
                box.toggled.connect(lambda v, k=task.manual: self._tick(k, v))
                grid.addWidget(box, r, 0, 1, 2)
            else:
                state = "ok" if done else "warning" if done is False else None
                grid.addWidget(_ampel(state) if state else QLabel("•"), r, 0)
                label = QLabel(task.text if not done else f"{task.text}  ✓")
                label.setWordWrap(True)
                if task.auto and not done:
                    label.setToolTip(checks[task.auto].detail)
                grid.addWidget(label, r, 1)
            if task.link:
                btn = button(task.link_text or "Öffnen",
                             lambda _=False, k=task.link: self.action.emit(k),
                             tooltip=task.link_text or task.text)
                grid.addWidget(btn, r, 2)
        grid.setColumnStretch(1, 1)
        lay.addLayout(grid)
        lay.addStretch()
        if t.phase == "preparation":
            lay.addWidget(QLabel("Helfereinteilung (Notizen)", objectName="fieldLabel"))
            notes = QPlainTextEdit(checklist.get(ts.CHECKLIST_NOTES_KEY, ""))
            notes.setPlaceholderText("z. B. Anna: Kasse, Ben: Parcours A-D, …")
            notes.setFixedHeight(90)
            lay.addWidget(notes)
            lay.addWidget(button("Notizen speichern",
                                 lambda: self._save_note(ts.CHECKLIST_NOTES_KEY,
                                                         notes.toPlainText()),
                                 tooltip="Helfereinteilung speichern"))
        return card

    def _conditions_card(self, t, nxt) -> QFrame:
        card, lay = _card(f"Voraussetzungen für „{ts.PHASE_LABELS[nxt]}“")
        for c in ts.get_phase_conditions(t.id, nxt):
            row = QHBoxLayout()
            row.addWidget(_ampel("ok" if c.ok else c.severity))
            label = QLabel(c.label if c.ok else c.message)
            label.setWordWrap(True)
            label.setToolTip("Muss erfüllt sein" if c.severity == "blocker"
                             else "Hinweis, Wechsel trotzdem möglich")
            row.addWidget(label, 1)
            lay.addLayout(row)
        legend = QLabel("Rot = muss erfüllt sein · Gelb = Hinweis · Grün = erledigt",
                        objectName="pageSubtitle")
        legend.setWordWrap(True)
        lay.addWidget(legend)
        return card

    def _checks_card(self, t, checks) -> QFrame:
        card, lay = _card("Status")
        for key in PHASE_CHECKS[t.phase]:
            c = checks[key]
            row = QHBoxLayout()
            row.addWidget(_ampel("ok" if c.ok else "warning"))
            label = QLabel(c.label if c.ok else f"{c.label}: {c.detail}")
            label.setWordWrap(True)
            row.addWidget(label, 1)
            lay.addLayout(row)
        return card

    def _phase_card(self, t, checklist) -> QFrame | None:
        stats = ts.get_tournament_stats(t.id)
        if t.phase == "registration":
            card, lay = _card("Anmeldungen")
            s = stats.by_status
            lay.addWidget(QLabel(
                f"<b>{stats.total}</b> angemeldet · <b>{s['confirmed'] + s['checked_in']}</b> "
                f"bestätigt · <b>{stats.paid}</b> bezahlt · <b>{s['registered']}</b> offen"))
            bar = CapacityBar()
            bar.set_capacity(stats.capacity)
            lay.addWidget(bar)
            return card
        if t.phase == "checkin":
            card, lay = _card("Einschreibung")
            lay.addWidget(QLabel(f"{stats.by_status['checked_in']} eingecheckt / "
                                 f"{stats.expected} erwartet", objectName="bigCounter"))
            bar = CapacityBar()
            bar.set_capacity(stats.capacity)
            lay.addWidget(bar)
            return card
        if t.phase == "shooting":
            prog = ts.get_completion_progress(t.id)
            card, lay = _card("Ergebnisfortschritt")
            lay.addWidget(QLabel(f"{prog.entered} von {prog.needed} Wertungen eingetragen "
                                 f"({prog.percentage:.0f} %)"))
            bar = ProgressBar()
            bar.set_value(prog.percentage)
            lay.addWidget(bar)
            for cp in prog.per_class:
                lay.addWidget(QLabel(f"{cp.bow_class}: {cp.complete} / {cp.checked_in or cp.participants} "
                                     "vollständig", objectName="pageSubtitle"))
            return card
        if t.phase == "scoring":
            rev = ts.get_revenue_summary(t.id)
            card, lay = _card("Ausstehende Zahlungen")
            lay.addWidget(QLabel(
                f"{stats.unpaid} Teilnehmer · {rev.outstanding:.2f} € offen".replace(".", ","),
                objectName="dangerText" if stats.unpaid else "successText"))
            return card
        if t.phase == "closed":
            rev = ts.get_revenue_summary(t.id)
            card, lay = _card("Zusammenfassung")
            lay.addWidget(QLabel(
                f"{t.date:%d.%m.%Y} · {stats.total - stats.by_status['withdrawn']} Teilnehmer · "
                f"Einnahmen {rev.received:.2f} €".replace(".", ",")))
            lay.addWidget(QLabel("Nachbesprechung", objectName="fieldLabel"))
            notes = QPlainTextEdit(checklist.get(DEBRIEF_KEY, ""))
            notes.setPlaceholderText("Was lief gut, was verbessern wir beim nächsten Turnier?")
            notes.setFixedHeight(120)
            lay.addWidget(notes)
            lay.addWidget(button("Notizen speichern",
                                 lambda: self._save_note(DEBRIEF_KEY, notes.toPlainText()),
                                 tooltip="Nachbesprechung speichern"))
            return card
        return None

    # ------------------------------------------------------------ actions
    def _tick(self, key: str, value: bool):
        ts.set_checklist_item(self.tid, key, value)
        context.notify()

    def _save_note(self, key: str, text: str):
        ts.set_checklist_item(self.tid, key, text.strip())
        Toast.show(self, "Notizen gespeichert", Toast.SUCCESS)
