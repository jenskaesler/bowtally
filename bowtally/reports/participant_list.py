# -*- coding: utf-8 -*-
"""Check-in list for the registration desk: one row per participant with signature column."""
import re
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from bowtally import config
from bowtally.reports import templates as tpl
from bowtally.services import settings_service as ss
from bowtally.services import tournament_service as ts
from bowtally.services.participant_service import PAYMENT_LABELS

HEADERS = ["Nr.", "Name", "Verein", "Klasse", "Gruppe", "Startgeld", "Bezahlt", "Unterschrift"]


def checkin_list_path(tournament_id: int) -> Path:
    config.PDF_TEMP_DIR.mkdir(parents=True, exist_ok=True)
    t = ts.get_tournament(tournament_id)
    safe = re.sub(r"[^\w-]+", "_", t.name).strip("_") or "Turnier"
    return config.PDF_TEMP_DIR / f"Einschreibeliste_{safe}_{datetime.now():%Y%m%d_%H%M%S}.pdf"


def build_checkin_list(tournament_id: int, path: str | Path | None = None) -> Path:
    t = ts.get_tournament(tournament_id)
    path = Path(path) if path else checkin_list_path(tournament_id)
    settings = ss.get_all()
    primary = colors.HexColor(settings.get(ss.KEY_COLOR_PRIMARY) or "#00357D")
    border = colors.HexColor(settings.get(ss.KEY_COLOR_BORDER) or "#D0D7E0")
    font, bold = tpl.register_fonts([settings.get(ss.KEY_FONT_FAMILY) or "Open Sans",
                                     "Segoe UI", "Arial"])
    title = ParagraphStyle("t", fontName=bold, fontSize=15, leading=19, textColor=primary)
    sub = ParagraphStyle("s", fontName=font, fontSize=9, leading=12)
    pagesize = tpl.page_size("A4", "landscape")
    parts = sorted((p for p in t.participants if ts.is_active_participant(p)),
                   key=lambda p: (p.start_number or 10**9, p.archer.last_name))
    rows = [HEADERS] + [[
        p.start_number or "", f"{p.archer.last_name}, {p.archer.first_name}",
        p.archer.club or "", p.bow_class.abbreviation or p.bow_class.name if p.bow_class else "",
        p.start_group or "",
        f"{p.entry_fee.amount:.2f} €".replace(".", ",") if p.entry_fee else "–",
        PAYMENT_LABELS.get(p.payment_status, ""), ""] for p in parts]
    width = pagesize[0] - tpl.MARGIN_LEFT - tpl.MARGIN_RIGHT
    widths = [12 * mm, 55 * mm, 50 * mm, 22 * mm, 18 * mm, 24 * mm, 24 * mm]
    widths.append(width - sum(widths))
    table = Table(rows, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font), ("FONTNAME", (0, 0), (-1, 0), bold),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), primary), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, border),
        ("ALIGN", (0, 0), (0, -1), "RIGHT"), ("ALIGN", (5, 0), (5, -1), "RIGHT"),
        ("TOPPADDING", (0, 1), (-1, -1), 7), ("BOTTOMPADDING", (0, 1), (-1, -1), 7),
    ]))
    doc = SimpleDocTemplate(str(path), pagesize=pagesize, leftMargin=tpl.MARGIN_LEFT,
                            rightMargin=tpl.MARGIN_RIGHT, topMargin=tpl.MARGIN_TOP,
                            bottomMargin=tpl.MARGIN_BOTTOM, title=f"Einschreibeliste {t.name}",
                            creator="BowTally")
    doc.build([Paragraph(f"Einschreibeliste – {t.name}", title),
               Paragraph(f"{t.date:%d.%m.%Y} · {len(parts)} Teilnehmer · erstellt "
                         f"{datetime.now():%d.%m.%Y %H:%M}", sub),
               Spacer(1, 5 * mm), table])
    return path
