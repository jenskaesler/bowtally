# -*- coding: utf-8 -*-
"""Erweiterte Druckansichten: Starterfeld-Liste und Gruppen-Aushang."""
import re
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

from bowtally import config
from bowtally.reports import templates as tpl
from bowtally.services import course_service as cs
from bowtally.services import settings_service as ss
from bowtally.services.tournament_service import get_tournament, is_active_participant


def _path(tournament_id: int, label: str) -> Path:
    t = get_tournament(tournament_id)
    safe = re.sub(r"[^\w-]+", "_", t.name).strip("_") or "Turnier"
    return config.export_dir() / f"{label}_{safe}_{datetime.now():%Y%m%d_%H%M%S}.pdf"


def _common(settings):
    primary = colors.HexColor(settings.get(ss.KEY_COLOR_PRIMARY) or "#00357D")
    border = colors.HexColor(settings.get(ss.KEY_COLOR_BORDER) or "#D0D7E0")
    font, bold = tpl.register_fonts([settings.get(ss.KEY_FONT_FAMILY) or "Open Sans",
                                     "Segoe UI", "Arial"])
    return primary, border, font, bold


def build_starter_list(tournament_id: int, sort_by: str = "number",
                       path: str | Path | None = None) -> Path:
    """Starterfeld: alle aktiven Teilnehmer, sortiert nach Startnummer oder Gruppe."""
    path = Path(path) if path else _path(tournament_id, "Starterfeld")
    t = get_tournament(tournament_id)
    settings = ss.get_all()
    primary, border, font, bold = _common(settings)
    pagesize = tpl.page_size("A4", "portrait")
    page_w = pagesize[0] - tpl.MARGIN_LEFT - tpl.MARGIN_RIGHT

    parts = [p for p in t.participants if is_active_participant(p)]
    title_s = ParagraphStyle("t", fontName=bold, fontSize=15, leading=19, textColor=primary)
    sub_s = ParagraphStyle("s", fontName=font, fontSize=9, leading=12)
    grp_s = ParagraphStyle("g", fontName=bold, fontSize=11, leading=14, textColor=primary)

    def _part_table(members):
        headers = ["St.-Nr.", "Name", "Verein", "Klasse"]
        rows = [headers] + [[
            p.start_number or "",
            f"{p.archer.last_name}, {p.archer.first_name}",
            p.archer.club or "",
            p.bow_class.abbreviation or p.bow_class.name if p.bow_class else "",
        ] for p in members]
        cw = [18 * mm, None, 55 * mm, 22 * mm]
        cw[1] = page_w - sum(w for w in cw if w)
        tbl = Table(rows, colWidths=cw, repeatRows=1)
        tbl.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), font), ("FONTNAME", (0, 0), (-1, 0), bold),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 0), (-1, 0), primary), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("LINEBELOW", (0, 0), (-1, -1), 0.3, border),
            ("TOPPADDING", (0, 1), (-1, -1), 5), ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        ]))
        return tbl

    sort_label = "Startgruppe" if sort_by == "group" else "Startnummer"
    story = [
        Paragraph("Starterfeld: " + t.name, title_s),
        Spacer(1, 2 * mm),
        Paragraph(f"{t.date:%d.%m.%Y}" + (f" · {t.location}" if t.location else "")
                  + f" · {len(parts)} Teilnehmer · sortiert nach {sort_label}", sub_s),
        Spacer(1, 6 * mm),
    ]

    if sort_by == "group":
        parts.sort(key=lambda p: (p.start_group or "\xff", p.start_number or 0, p.archer.last_name))
        groups: dict[str, list] = {}
        for p in parts:
            groups.setdefault(p.start_group or "", []).append(p)
        for key in sorted(groups, key=lambda k: (k == "", k)):
            label = key if key else "Ohne Gruppe"
            story.append(Paragraph(label, grp_s))
            story.append(Spacer(1, 2 * mm))
            story.append(_part_table(groups[key]))
            story.append(Spacer(1, 6 * mm))
    else:
        parts.sort(key=lambda p: (p.start_number or 10**9, p.archer.last_name))
        story.append(_part_table(parts))
    doc = SimpleDocTemplate(str(path), pagesize=pagesize,
                            leftMargin=tpl.MARGIN_LEFT, rightMargin=tpl.MARGIN_RIGHT,
                            topMargin=tpl.MARGIN_TOP, bottomMargin=tpl.MARGIN_BOTTOM)
    doc.build(story)
    return path


def build_group_poster(tournament_id: int, path: str | Path | None = None) -> Path:
    """Gruppen-Aushang: je Gruppe eine Seite mit Teilnehmern und Scheibennummern."""
    path = Path(path) if path else _path(tournament_id, "Gruppen_Aushang")
    t = get_tournament(tournament_id)
    settings = ss.get_all()
    primary, border, font, bold = _common(settings)
    targets = cs.list_targets(tournament_id)
    target_by_num = {tgt.number: tgt for tgt in targets}
    pagesize = tpl.page_size("A4", "portrait")
    page_w = pagesize[0] - tpl.MARGIN_LEFT - tpl.MARGIN_RIGHT

    parts = [p for p in t.participants if is_active_participant(p)]
    # group participants
    groups: dict[str, list] = {}
    ungrouped = []
    for p in parts:
        if p.start_group:
            groups.setdefault(p.start_group, []).append(p)
        else:
            ungrouped.append(p)
    if ungrouped:
        groups["(keine Gruppe)"] = ungrouped

    title_s = ParagraphStyle("t", fontName=bold, fontSize=20, leading=26, textColor=primary)
    sub_s = ParagraphStyle("s", fontName=font, fontSize=10, leading=14)
    name_s = ParagraphStyle("n", fontName=font, fontSize=13, leading=18)
    name_b = ParagraphStyle("nb", fontName=bold, fontSize=13, leading=18)

    story = []
    for gi, (group_name, members) in enumerate(sorted(groups.items())):
        if gi > 0:
            story.append(PageBreak())
        story.append(Paragraph("Gruppe " + group_name, title_s))
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(t.name + " · " + f"{t.date:%d.%m.%Y}", sub_s))
        story.append(Spacer(1, 6 * mm))

        # start target info
        start_targets = sorted({p.start_time for p in members if p.start_time})
        if start_targets:
            story.append(Paragraph("Startscheibe: " + ", ".join(start_targets), sub_s))
            story.append(Spacer(1, 4 * mm))

        # participant list
        members_sorted = sorted(members, key=lambda p: (p.start_number or 0, p.archer.last_name))
        for p in members_sorted:
            name_text = f"{p.archer.last_name}, {p.archer.first_name}"
            cls = p.bow_class.abbreviation or p.bow_class.name if p.bow_class else ""
            num = f"  [Nr. {p.start_number}]" if p.start_number else ""
            story.append(Paragraph(f"{name_text}{num}   {cls}", name_s))

        # target table (if course_targets defined)
        if targets:
            story.append(Spacer(1, 8 * mm))
            story.append(Paragraph("Scheiben:", sub_s))
            story.append(Spacer(1, 2 * mm))
            tgt_rows = [["Nr.", "Tier / Scheibe", "Distanz", "Pfeilstopp"]]
            for tgt in targets:
                tgt_rows.append([str(tgt.number), tgt.animal_name or "",
                                  f"{tgt.distance_m:.0f} m" if tgt.distance_m else "",
                                  tgt.arrow_stop_class or ""])
            tgt_table = Table(tgt_rows, colWidths=[14 * mm, None, 22 * mm, 28 * mm],
                              repeatRows=1)
            tgt_table._argW[1] = page_w - 64 * mm
            tgt_table.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, -1), font), ("FONTNAME", (0, 0), (-1, 0), bold),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BACKGROUND", (0, 0), (-1, 0), primary),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("LINEBELOW", (0, 0), (-1, -1), 0.3, border),
                ("TOPPADDING", (0, 1), (-1, -1), 4), ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
            ]))
            story.append(tgt_table)

    if not story:
        story.append(Paragraph("Keine Gruppen vorhanden.", ParagraphStyle(
            "e", fontName=font, fontSize=10)))

    doc = SimpleDocTemplate(str(path), pagesize=pagesize,
                            leftMargin=tpl.MARGIN_LEFT, rightMargin=tpl.MARGIN_RIGHT,
                            topMargin=tpl.MARGIN_TOP, bottomMargin=tpl.MARGIN_BOTTOM)
    doc.build(story)
    return path
