# -*- coding: utf-8 -*-
"""Wertungszettel-PDF: ein Zettel pro Teilnehmer mit Turnier-Kopf und Bewertungstabelle."""
import re
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

from bowtally import config
from bowtally.reports import templates as tpl
from bowtally.services import course_service as cs
from bowtally.services import score_sheet_service as sss
from bowtally.services import settings_service as ss
from bowtally.services.tournament_service import get_tournament, is_active_participant

_HEADER_LABELS = {
    "name": "Name",
    "bow_class": "Klasse",
    "start_number": "Startnr.",
    "start_group": "Gruppe",
    "club": "Verein",
}


def _path(tournament_id: int) -> Path:
    t = get_tournament(tournament_id)
    safe = re.sub(r"[^\w-]+", "_", t.name).strip("_") or "Turnier"
    return config.export_dir() / f"Wertungszettel_{safe}_{datetime.now():%Y%m%d_%H%M%S}.pdf"


def build_score_sheets(tournament_id: int, template_id: int,
                       path: str | Path | None = None) -> Path:
    path = Path(path) if path else _path(tournament_id)
    t = get_tournament(tournament_id)
    tmpl = sss.get_template(template_id)
    if tmpl is None:
        raise ValueError("Wertungszettel-Vorlage nicht gefunden")

    columns = sss.columns(tmpl)
    hdr_fields = sss.header_fields(tmpl)
    targets = cs.list_targets(tournament_id)
    participants = sorted(
        [p for p in t.participants if is_active_participant(p)],
        key=lambda p: (p.start_group or "", p.start_number or 0, p.archer.last_name))

    settings = ss.get_all()
    club = ss.get_club_profile()
    primary = colors.HexColor(settings.get(ss.KEY_COLOR_PRIMARY) or "#00357D")
    border = colors.HexColor(settings.get(ss.KEY_COLOR_BORDER) or "#D0D7E0")
    font, bold = tpl.register_fonts([settings.get(ss.KEY_FONT_FAMILY) or "Open Sans",
                                     "Segoe UI", "Arial"])
    pagesize = tpl.page_size("A4", "portrait")
    page_w = pagesize[0] - tpl.MARGIN_LEFT - tpl.MARGIN_RIGHT

    title_s = ParagraphStyle("t", fontName=bold, fontSize=13, leading=17, textColor=primary)
    sub_s = ParagraphStyle("s", fontName=font, fontSize=9, leading=12)
    cell_s = ParagraphStyle("c", fontName=font, fontSize=9, leading=12)

    logo_img = None
    if ss.get_bool(ss.KEY_PRINT_SHOW_LOGO):
        logo_img = _logo(club.get("logo_path"))

    story = []
    for idx, p in enumerate(participants):
        if idx > 0:
            story.append(PageBreak())

        # --- Header block
        header_data = [[_participant_header_table(p, hdr_fields, t, font, bold, primary, page_w,
                                                  logo_img)]]
        story.append(Paragraph(t.name, title_s))
        story.append(Spacer(1, 2 * mm))

        # participant info row
        info_parts = []
        for field in hdr_fields:
            val = _field_value(p, field)
            if val:
                info_parts.append(f"<b>{_HEADER_LABELS.get(field, field)}:</b> {val}")
        story.append(Paragraph("   ·   ".join(info_parts), sub_s))
        story.append(Spacer(1, 4 * mm))

        # --- Scoring table
        col_names = [c["name"] for c in columns]
        if targets:
            tbl_headers = ["Nr.", "Tier / Scheibe"] + col_names + ["∑"]
            widths = [12 * mm, None] + [c.get("width_mm", 14) * mm for c in columns] + [16 * mm]
            fixed_w = sum(w for w in widths if w is not None)
            widths[1] = page_w - fixed_w
            rows = [tbl_headers]
            for tgt in targets:
                rows.append([str(tgt.number), tgt.animal_name or ""] + [""] * len(columns) + [""])
        else:
            # no targets: use plain numbered rows from tournament.num_targets
            tbl_headers = ["Nr."] + col_names + ["∑"]
            widths = [12 * mm] + [c.get("width_mm", 14) * mm for c in columns] + [16 * mm]
            fixed_w = sum(widths)
            rows = [tbl_headers]
            for n_i in range(1, (t.num_targets or 24) + 1):
                rows.append([str(n_i)] + [""] * (len(columns) + 1))

        # total row
        rows.append(["", "Gesamt"] + [""] * len(columns) + [""])

        scoring_table = Table(rows, colWidths=widths, repeatRows=1)
        scoring_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), font),
            ("FONTNAME", (0, 0), (-1, 0), bold),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 0), (-1, 0), primary),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("LINEBELOW", (0, 0), (-1, -1), 0.3, border),
            ("LINEBEFORE", (0, 0), (-1, -1), 0.3, border),
            ("ALIGN", (0, 0), (0, -1), "RIGHT"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2),
             [colors.white, colors.HexColor("#F8F9FB")]),
            ("FONTNAME", (0, -1), (-1, -1), bold),
            ("TOPPADDING", (0, 1), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        ]))
        story.append(scoring_table)
        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph("Unterschrift: ___________________________", sub_s))

    doc = SimpleDocTemplate(str(path), pagesize=pagesize,
                            leftMargin=tpl.MARGIN_LEFT, rightMargin=tpl.MARGIN_RIGHT,
                            topMargin=tpl.MARGIN_TOP, bottomMargin=tpl.MARGIN_BOTTOM)
    doc.build(story)
    return path


def _field_value(p, field: str) -> str:
    if field == "name":
        return f"{p.archer.last_name}, {p.archer.first_name}"
    if field == "bow_class":
        return p.bow_class.name if p.bow_class else ""
    if field == "start_number":
        return str(p.start_number) if p.start_number else ""
    if field == "start_group":
        return p.start_group or ""
    if field == "club":
        return p.archer.club or ""
    return ""


def _logo(path: str | None):
    if not path or not Path(path).is_file():
        return None
    try:
        from reportlab.platypus import Image as Img
        img = Img(path)
        ratio = min(40 * mm / img.imageWidth, 20 * mm / img.imageHeight)
        img.drawWidth, img.drawHeight = img.imageWidth * ratio, img.imageHeight * ratio
        return img
    except Exception:
        return None
