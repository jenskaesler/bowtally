# -*- coding: utf-8 -*-
"""PDF reports for parcours planning: Aufbauplan (with notes) and Zielplan (without notes)."""
import re
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from bowtally import config
from bowtally.reports import templates as tpl
from bowtally.services import course_service as cs
from bowtally.services import settings_service as ss
from bowtally.services import tournament_service as ts


def _path(tournament_id: int, label: str) -> Path:
    t = ts.get_tournament(tournament_id)
    safe = re.sub(r"[^\w-]+", "_", t.name).strip("_") or "Turnier"
    return config.export_dir() / f"{label}_{safe}_{datetime.now():%Y%m%d_%H%M%S}.pdf"


def build_course_plan(tournament_id: int, with_notes: bool = True,
                      path: str | Path | None = None) -> Path:
    label = "Aufbauplan" if with_notes else "Zielplan"
    path = Path(path) if path else _path(tournament_id, label)
    t = ts.get_tournament(tournament_id)
    targets = cs.list_targets(tournament_id)
    settings = ss.get_all()
    primary = colors.HexColor(settings.get(ss.KEY_PRINT_COLOR_PRIMARY) or "#00357D")
    border = colors.HexColor(settings.get(ss.KEY_PRINT_COLOR_BORDER) or "#D0D7E0")
    font, bold = tpl.register_fonts([settings.get(ss.KEY_FONT_FAMILY) or "Open Sans",
                                     "Segoe UI", "Arial"])
    title_style = ParagraphStyle("t", fontName=bold, fontSize=15, leading=19, textColor=primary)
    sub_style = ParagraphStyle("s", fontName=font, fontSize=9, leading=12)
    pagesize = tpl.page_size("A4", "portrait")
    width = pagesize[0] - tpl.MARGIN_LEFT - tpl.MARGIN_RIGHT

    headers = ["Nr.", "Tier / Scheibe", "Distanz (m)", "Pfeilstopp", "Gelände", "Max. Gruppe"]
    if with_notes:
        headers.append("Helfernotiz")

    rows = [headers]
    for tgt in targets:
        row = [
            str(tgt.number),
            tgt.animal_name or "–",
            f"{tgt.distance_m:.1f}" if tgt.distance_m else "–",
            tgt.arrow_stop_class or "–",
            tgt.terrain_type or "–",
            str(tgt.max_group_size) if tgt.max_group_size else "–",
        ]
        if with_notes:
            row.append(tgt.helper_note or "")
        rows.append(row)

    if with_notes:
        col_widths = [12 * mm, None, 22 * mm, 28 * mm, 28 * mm, 24 * mm, None]
        fixed = sum(w for w in col_widths if w is not None)
        remaining = width - fixed
        col_widths[1] = remaining * 0.45
        col_widths[6] = remaining * 0.55
    else:
        col_widths = [12 * mm, None, 22 * mm, 28 * mm, 28 * mm, 24 * mm]
        fixed = sum(w for w in col_widths if w is not None)
        col_widths[1] = width - fixed

    table = Table(rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font),
        ("FONTNAME", (0, 0), (-1, 0), bold),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), primary),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, border),
        ("ALIGN", (0, 0), (0, -1), "RIGHT"),
        ("ALIGN", (2, 0), (2, -1), "RIGHT"),
        ("TOPPADDING", (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))

    story = [
        Paragraph(f"{label}: {t.name}", title_style),
        Spacer(1, 4 * mm),
        Paragraph(f"{t.date:%d.%m.%Y}" + (f" · {t.location}" if t.location else "")
                  + f" · {len(targets)} Scheibe{'n' if len(targets) != 1 else ''}", sub_style),
        Spacer(1, 6 * mm),
        table,
    ]
    doc = SimpleDocTemplate(str(path), pagesize=pagesize,
                            leftMargin=tpl.MARGIN_LEFT, rightMargin=tpl.MARGIN_RIGHT,
                            topMargin=tpl.MARGIN_TOP, bottomMargin=tpl.MARGIN_BOTTOM)
    doc.build(story, canvasmaker=tpl.WatermarkCanvas)
    return path


def build_schedule_plan(tournament_id: int, path: str | Path | None = None) -> Path:
    path = Path(path) if path else _path(tournament_id, "Zeitplan")
    t = ts.get_tournament(tournament_id)
    groups = cs.list_groups(tournament_id)
    # participant counts per group
    counts: dict[str, list[str]] = {}
    for p in t.participants:
        if p.start_group:
            counts.setdefault(p.start_group, []).append(
                f"{p.archer.last_name}, {p.archer.first_name}")
    settings = ss.get_all()
    primary = colors.HexColor(settings.get(ss.KEY_PRINT_COLOR_PRIMARY) or "#00357D")
    border = colors.HexColor(settings.get(ss.KEY_PRINT_COLOR_BORDER) or "#D0D7E0")
    font, bold = tpl.register_fonts([settings.get(ss.KEY_FONT_FAMILY) or "Open Sans",
                                     "Segoe UI", "Arial"])
    title_style = ParagraphStyle("t", fontName=bold, fontSize=15, leading=19, textColor=primary)
    sub_style = ParagraphStyle("s", fontName=font, fontSize=9, leading=12)
    cell_style = ParagraphStyle("c", fontName=font, fontSize=9, leading=12)
    pagesize = tpl.page_size("A4", "portrait")
    width = pagesize[0] - tpl.MARGIN_LEFT - tpl.MARGIN_RIGHT

    headers = ["Gruppe", "Startzeit", "Dauer", "Teilnehmer"]
    rows = [headers]
    for g in groups:
        names = ", ".join(sorted(counts.get(g.group_name, [])))
        dur = f"{g.estimated_duration_min} min" if g.estimated_duration_min else "–"
        rows.append([g.group_name, g.start_time or "–", dur,
                     Paragraph(names, cell_style) if names else "–"])

    col_widths = [30 * mm, 24 * mm, 22 * mm, width - 76 * mm]
    table = Table(rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font),
        ("FONTNAME", (0, 0), (-1, 0), bold),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), primary),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, border),
        ("TOPPADDING", (0, 1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))

    story = [
        Paragraph(f"Zeitplan: {t.name}", title_style),
        Spacer(1, 4 * mm),
        Paragraph(f"{t.date:%d.%m.%Y}" + (f" · {t.location}" if t.location else "")
                  + f" · {len(groups)} Gruppe{'n' if len(groups) != 1 else ''}", sub_style),
        Spacer(1, 6 * mm),
        table,
    ]
    doc = SimpleDocTemplate(str(path), pagesize=pagesize,
                            leftMargin=tpl.MARGIN_LEFT, rightMargin=tpl.MARGIN_RIGHT,
                            topMargin=tpl.MARGIN_TOP, bottomMargin=tpl.MARGIN_BOTTOM)
    doc.build(story, canvasmaker=tpl.WatermarkCanvas)
    return path
