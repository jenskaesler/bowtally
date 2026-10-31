# -*- coding: utf-8 -*-
"""Preis- und Siegerliste als PDF: Rangliste mit Preis je Klasse und Platz."""
import re
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

from bowtally import config
from bowtally.reports import templates as tpl
from bowtally.services import prize_service as ps
from bowtally.services import ranking_service as rs
from bowtally.services import settings_service as ss
from bowtally.services.tournament_service import get_tournament


def _path(tournament_id: int) -> Path:
    t = get_tournament(tournament_id)
    safe = re.sub(r"[^\w-]+", "_", t.name).strip("_") or "Turnier"
    return config.export_dir() / f"Preis_Siegerliste_{safe}_{datetime.now():%Y%m%d_%H%M%S}.pdf"


def build_prize_list(tournament_id: int, path: str | Path | None = None) -> Path:
    path = Path(path) if path else _path(tournament_id)
    t = get_tournament(tournament_id)
    prizes = ps.list_prizes(tournament_id)
    per_class = rs.compute_ranking(tournament_id)
    bow_classes = {bc.id: bc for bc in t.bow_classes}

    settings = ss.get_all()
    primary = colors.HexColor(settings.get(ss.KEY_COLOR_PRIMARY) or "#00357D")
    border = colors.HexColor(settings.get(ss.KEY_COLOR_BORDER) or "#D0D7E0")
    font, bold = tpl.register_fonts([settings.get(ss.KEY_FONT_FAMILY) or "Open Sans",
                                     "Segoe UI", "Arial"])
    pagesize = tpl.page_size("A4", "portrait")
    page_w = pagesize[0] - tpl.MARGIN_LEFT - tpl.MARGIN_RIGHT

    title_s = ParagraphStyle("t", fontName=bold, fontSize=15, leading=19, textColor=primary)
    sub_s = ParagraphStyle("s", fontName=font, fontSize=9, leading=12)
    head_s = ParagraphStyle("h", fontName=bold, fontSize=11, leading=15, textColor=primary,
                            spaceAfter=4)
    center_s = ParagraphStyle("c", fontName=font, fontSize=9, leading=12,
                               alignment=TA_CENTER)

    # Build prize lookup: {bow_class_id_or_None: {rank: prize}}
    prize_map: dict = {}
    for p in prizes:
        prize_map.setdefault(p.bow_class_id, {})[p.rank] = p

    story = [
        Paragraph("Preis- und Siegerliste: " + t.name, title_s),
        Spacer(1, 2 * mm),
        Paragraph(f"{t.date:%d.%m.%Y}" + (f" · {t.location}" if t.location else ""), sub_s),
        Spacer(1, 6 * mm),
    ]

    for bc_id, rank_rows in per_class.items():
        bc = bow_classes.get(bc_id)
        # prizes for this class + global prizes
        class_prizes = {**prize_map.get(None, {}), **prize_map.get(bc_id, {})}

        story.append(Paragraph(bc.name if bc else "Allgemein", head_s))
        rows = [["Platz", "Name", "Verein", "Punkte", "Preis"]]
        for entry in rank_rows[:max(10, len(class_prizes))]:
            prize = class_prizes.get(entry.rank)
            rows.append([
                str(entry.rank),
                entry.name,
                entry.club or "",
                str(entry.total),
                prize.name if prize else "",
            ])
        table = Table(rows, colWidths=[16 * mm, None, 50 * mm, 20 * mm, 50 * mm],
                      repeatRows=1)
        table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), font),
            ("FONTNAME", (0, 0), (-1, 0), bold),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 0), (-1, 0), primary),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("LINEBELOW", (0, 0), (-1, -1), 0.3, border),
            ("TOPPADDING", (0, 1), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        ]))
        # fix name column width
        col_widths = [16 * mm, page_w - 136 * mm, 50 * mm, 20 * mm, 50 * mm]
        table._argW = col_widths
        story.append(table)
        story.append(Spacer(1, 8 * mm))

    doc = SimpleDocTemplate(str(path), pagesize=pagesize,
                            leftMargin=tpl.MARGIN_LEFT, rightMargin=tpl.MARGIN_RIGHT,
                            topMargin=tpl.MARGIN_TOP, bottomMargin=tpl.MARGIN_BOTTOM)
    doc.build(story)
    return path
