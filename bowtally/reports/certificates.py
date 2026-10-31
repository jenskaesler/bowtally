# -*- coding: utf-8 -*-
"""Urkunden-PDF: eine Seite pro Teilnehmer, konfigurierbare Vorlage mit Platzhaltern."""
import re
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (PageBreak, Paragraph, SimpleDocTemplate, Spacer)

from bowtally import config
from bowtally.reports import templates as tpl
from bowtally.services import ranking_service as rs
from bowtally.services import settings_service as ss
from bowtally.services.tournament_service import get_tournament

# Default template stored in AppSettings under this key
KEY_CERT_BG = "cert_background_color"
KEY_CERT_FONT_SIZE = "cert_font_size"
KEY_CERT_BLOCKS = "cert_text_blocks"

DEFAULT_BLOCKS = [
    {"text": "{turniername}", "y_pct": 0.30, "size_pt": 18, "bold": True},
    {"text": "Urkunde", "y_pct": 0.42, "size_pt": 28, "bold": True},
    {"text": "{name}", "y_pct": 0.52, "size_pt": 20, "bold": False},
    {"text": "{klasse}", "y_pct": 0.59, "size_pt": 13, "bold": False},
    {"text": "Platz {platz}  ·  {punkte} Punkte", "y_pct": 0.67, "size_pt": 16, "bold": True},
    {"text": "{datum}", "y_pct": 0.80, "size_pt": 11, "bold": False},
]


def _path(tournament_id: int) -> Path:
    t = get_tournament(tournament_id)
    safe = re.sub(r"[^\w-]+", "_", t.name).strip("_") or "Turnier"
    return config.export_dir() / f"Urkunden_{safe}_{datetime.now():%Y%m%d_%H%M%S}.pdf"


def build_certificates(tournament_id: int, path: str | Path | None = None) -> Path:
    """Generate one A4 certificate per ranked participant (podium only by default)."""
    path = Path(path) if path else _path(tournament_id)
    t = get_tournament(tournament_id)
    per_class = rs.compute_ranking(tournament_id)
    bow_classes = {bc.id: bc for bc in t.bow_classes}
    settings = ss.get_all()
    font, bold_font = tpl.register_fonts([settings.get(ss.KEY_FONT_FAMILY) or "Open Sans",
                                          "Segoe UI", "Arial"])
    import json
    blocks = DEFAULT_BLOCKS
    bg_hex = settings.get(KEY_CERT_BG) or "#FFFFFF"
    bg_color = colors.HexColor(bg_hex)
    primary = colors.HexColor(settings.get(ss.KEY_COLOR_PRIMARY) or "#00357D")

    pagesize = tpl.page_size("A4", "portrait")
    page_h = pagesize[1]
    page_w = pagesize[0]

    story = []
    first = True
    for bc_id, rank_rows in per_class.items():
        bc = bow_classes.get(bc_id)
        for entry in rank_rows[:tpl.PODIUM_PLACES]:
            if not first:
                story.append(PageBreak())
            first = False
            placeholders = {
                "turniername": t.name,
                "name": entry.name,
                "klasse": bc.name if bc else "",
                "platz": str(entry.rank),
                "punkte": str(entry.total),
                "datum": f"{t.date:%d.%m.%Y}",
            }
            for block in blocks:
                text = block["text"]
                for k, v in placeholders.items():
                    text = text.replace("{" + k + "}", v)
                fn = bold_font if block.get("bold") else font
                size = block.get("size_pt", 12)
                y_pct = block.get("y_pct", 0.5)
                space_before = y_pct * page_h - tpl.MARGIN_TOP
                if space_before > 0 and not story or not isinstance(story[-1], Spacer):
                    story.append(Spacer(1, max(0, space_before - size * 1.5)))
                style = ParagraphStyle("b", fontName=fn, fontSize=size,
                                       leading=size * 1.4, alignment=TA_CENTER,
                                       textColor=primary if block.get("bold") else colors.black)
                story.append(Paragraph(text, style))

    if not story:
        story.append(Paragraph("Keine Ranglisten-Einträge vorhanden.", ParagraphStyle(
            "e", fontName=font, fontSize=10)))

    doc = SimpleDocTemplate(str(path), pagesize=pagesize,
                            leftMargin=20 * mm, rightMargin=20 * mm,
                            topMargin=tpl.MARGIN_TOP, bottomMargin=tpl.MARGIN_BOTTOM)
    doc.build(story)
    return path
