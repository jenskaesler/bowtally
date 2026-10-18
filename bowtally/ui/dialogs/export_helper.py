# -*- coding: utf-8 -*-
"""Shared export flow: format dropdown, file dialog, write, success toast with 'Öffnen'."""
from typing import Callable

from PySide6.QtWidgets import QFileDialog, QMenu, QPushButton

from bowtally.io import exporter
from bowtally.ui import busy, button, show_error
from bowtally.ui.components.toast import Toast

FORMATS = [("Excel (.xlsx)", "Excel (*.xlsx)", ".xlsx"),
           ("OpenDocument (.ods)", "OpenDocument (*.ods)", ".ods"),
           ("CSV (.csv)", "CSV (*.csv)", ".csv")]


def export_button(parent, default_stem: str, sheets: Callable[[bool], list],
                  filtered_count: Callable[[], int | None] = lambda: None,
                  text: str = "Exportieren") -> QPushButton:
    """sheets(filtered) -> [(name, headers, rows)]. filtered_count() -> N if a filter is active."""
    btn = button(text, tooltip="Als CSV, Excel oder OpenDocument exportieren")
    m = QMenu(btn)

    def rebuild():
        m.clear()
        n = filtered_count()
        groups = [(False, "Alle Datensätze")] + ([(True, f"Nur gefilterte ({n})")] if n else [])
        for filtered, title in groups:
            if len(groups) > 1:
                m.addSection(title)
            for label, flt, ext in FORMATS:
                m.addAction(label).triggered.connect(
                    lambda _=False, f=filtered, fl=flt, e=ext: run_export(
                        parent, default_stem + e, fl, sheets(f)))

    m.aboutToShow.connect(rebuild)
    btn.setMenu(m)
    return btn


def run_export(parent, default_name: str, file_filter: str, sheets: list) -> None:
    path, _ = QFileDialog.getSaveFileName(parent, "Exportieren", default_name, file_filter)
    if not path:
        return
    path = exporter.ensure_suffix(path, file_filter)
    try:
        with busy():
            written = exporter.write_sheets(path, sheets)
    except Exception as exc:
        show_error(parent, exc, "Export fehlgeschlagen")
        return
    extra = f" (+{len(written) - 1} weitere Dateien)" if len(written) > 1 else ""
    Toast.show(parent, f"Exportiert: {written[0].name}{extra}", Toast.SUCCESS,
               ("Öffnen", lambda: open_path(parent, written[0])))


def tournament_sheets(tournament_id: int) -> list:
    """All data of one tournament: participants, scores, ranking, fees."""
    from bowtally.services import ranking_service as rs
    from bowtally.services import scoring_service as sc
    from bowtally.services import tournament_service as ts
    from bowtally.services.participant_service import PAYMENT_LABELS, REGISTRATION_LABELS
    t = ts.get_tournament(tournament_id)
    parts = sorted(t.participants, key=lambda p: (p.start_number or 10**9, p.archer.last_name))
    participants = [[p.start_number, p.archer.last_name, p.archer.first_name, p.archer.club,
                     p.bow_class.name if p.bow_class else None, p.start_group,
                     REGISTRATION_LABELS.get(p.registration_status),
                     PAYMENT_LABELS.get(p.payment_status),
                     p.entry_fee.name if p.entry_fee else None, p.fee_amount_paid,
                     p.payment_date, p.registration_date, p.confirmation_date,
                     p.checkin_time.strftime("%d.%m.%Y %H:%M") if p.checkin_time else None,
                     p.notes] for p in parts]
    scores = sc.get_scores(tournament_id)
    cols = [(tg, s) for tg in range(1, t.num_targets + 1)
            for s in range(1, t.shots_per_target + 1)]
    score_rows = [[p.start_number, f"{p.archer.last_name}, {p.archer.first_name}"]
                  + [scores[(p.id, tg, s)].points if (p.id, tg, s) in scores else None
                     for tg, s in cols] for p in parts]
    ranking = rs.compute_ranking(tournament_id, overall=True)[rs.OVERALL]
    return [
        ("Teilnehmer", ["Nr.", "Nachname", "Vorname", "Verein", "Klasse", "Gruppe", "Anmeldung",
                        "Zahlung", "Startgebühr", "Bezahlt (EUR)", "Zahlungsdatum",
                        "Anmeldedatum", "Bestätigt am", "Eingecheckt", "Notizen"], participants),
        ("Ergebnisse", ["Nr.", "Name"] + [str(tg) if t.shots_per_target == 1 else f"{tg}.{s}"
                                          for tg, s in cols], score_rows),
        ("Rangliste", ["Rang", "Nr.", "Name", "Verein", "Klasse", "Gesamt"],
         [[r.rank, r.start_number, r.name, r.club, r.bow_class, r.total] for r in ranking]),
        ("Startgebühren", ["Name", "Betrag (EUR)", "Beschreibung"],
         [[f.name, f.amount, f.description] for f in t.fees]),
    ]


def open_path(parent, path) -> None:
    try:
        exporter.open_file(path)
    except OSError as exc:
        show_error(parent, exc, "Datei konnte nicht geöffnet werden")
