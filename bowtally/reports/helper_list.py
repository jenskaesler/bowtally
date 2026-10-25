# -*- coding: utf-8 -*-
"""Helper list PDF for one tournament."""
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
from bowtally.services.helper_service import list_tournament_helpers

HEADERS = ["Name", "Aufgabe", "Von", "Bis", "Bestätigt", "Telefon", "E-Mail"]


def helper_list_path(tournament_id: int) -> Path:
    config.PDF_TEMP_DIR.mkdir(parents=True, exist_ok=True)
    t = ts.get_tournament(tournament_id)
    safe = re.sub(r"[^\w-]+", "_", t.name).strip("_") or "Turnier"
    return config.PDF_TEMP_DIR / f"Helferliste_{safe}_{datetime.now():%Y%m%d_%H%M%S}.pdf"


def build_helper_list(tournament_id: int, path: str | Path | None = None) -> Path:
    t = ts.get_tournament(tournament_id)
    path = Path(path) if path else helper_list_path(tournament_id)
    settings = ss.get_all()
    primary = colors.HexColor(settings.get(ss.KEY_COLOR_PRIMARY) or "#00357D")
    border = colors.HexColor(settings.get(ss.KEY_COLOR_BORDER) or "#D0D7E0")
    font, bold = tpl.register_fonts([settings.get(ss.KEY_FONT_FAMILY) or "Open Sans",
                                     "Segoe UI", "Arial"])
    title_style = ParagraphStyle("t", fontName=bold, fontSize=15, leading=19, textColor=primary)
    sub_style = ParagraphStyle("s", fontName=font, fontSize=9, leading=12)
    pagesize = tpl.page_size("A4", "landscape")
    helpers = list_tournament_helpers(tournament_id)
    rows = [HEADERS] + [[
        f"{th.helper.last_name}, {th.helper.first_name}",
        th.task or "",
        th.time_from or "",
        th.time_to or "",
        "Ja" if th.confirmed else "Nein",
        th.helper.phone or "",
        th.helper.email or "",
    ] for th in helpers]
    usable_width = pagesize[0] - tpl.MARGIN_LEFT - tpl.MARGIN_RIGHT
    col_widths = [55 * mm, 75 * mm, 16 * mm, 16 * mm, 20 * mm, 38 * mm]
    col_widths.append(usable_width - sum(col_widths))
    table = Table(rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font), ("FONTNAME", (0, 0), (-1, 0), bold),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), primary), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, border),
        ("TOPPADDING", (0, 1), (-1, -1), 7), ("BOTTOMPADDING", (0, 1), (-1, -1), 7),
    ]))
    doc = SimpleDocTemplate(str(path), pagesize=pagesize, leftMargin=tpl.MARGIN_LEFT,
                            rightMargin=tpl.MARGIN_RIGHT, topMargin=tpl.MARGIN_TOP,
                            bottomMargin=tpl.MARGIN_BOTTOM, title=f"Helferliste {t.name}",
                            creator="BowTally")
    doc.build([Paragraph(f"Helferliste – {t.name}", title_style),
               Paragraph(f"{t.date:%d.%m.%Y} · {len(helpers)} Helfer · erstellt "
                         f"{datetime.now():%d.%m.%Y %H:%M}", sub_style),
               Spacer(1, 5 * mm), table])
    return path
