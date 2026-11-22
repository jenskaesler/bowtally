# -*- coding: utf-8 -*-
"""Turnierregeln als PDF: Turnier-Info und Allgemeine Turnierregeln."""
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from bowtally import config
from bowtally.reports import templates as tpl
from bowtally.reports.announcement import LOGO_HEADER, _esc, _logo, german_date
from bowtally.services import settings_service as ss
from bowtally.services import tournament_service as ts


def build_rules_pdf(tournament_id: int | None = None, path: str | Path | None = None) -> Path:
    """Aushang mit den globalen Turnierregeln; Turnier-Infos nur, wenn tournament_id gesetzt ist."""
    path = Path(path) if path else config.export_dir() / f"Turnierregeln_{datetime.now():%Y%m%d_%H%M%S}.pdf"
    settings = ss.get_all()
    club = ss.get_club_profile()
    primary = colors.HexColor(settings.get(ss.KEY_PRINT_COLOR_PRIMARY) or "#00357D")
    text2 = colors.HexColor(settings.get(ss.KEY_PRINT_COLOR_TEXT_SECONDARY) or "#777777")
    font, bold = tpl.register_fonts([settings.get(ss.KEY_FONT_FAMILY) or "Open Sans",
                                     "Segoe UI", "Arial"])
    title_s = ParagraphStyle("t", fontName=bold, fontSize=15, leading=19, textColor=primary)
    sub_s = ParagraphStyle("s", fontName=font, fontSize=9, leading=12, textColor=text2)
    body = ParagraphStyle("b", fontName=font, fontSize=10, leading=14)
    pagesize = tpl.page_size("A4", "portrait")
    created = datetime.now().strftime("%d.%m.%Y %H:%M")

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont(font, tpl.FONT_SIZE_FOOTER)
        canvas.setFillColor(text2)
        y = tpl.MARGIN_BOTTOM / 2
        canvas.drawString(tpl.MARGIN_LEFT, y, f"{tpl.FOOTER_TEXT} · {created}")
        canvas.drawCentredString(pagesize[0] / 2, y, f"Seite {doc.page}")
        canvas.restoreState()

    width = pagesize[0] - tpl.MARGIN_LEFT - tpl.MARGIN_RIGHT
    club_s = ParagraphStyle("c", fontName=bold, fontSize=16, leading=20)
    logo = _logo(club.get("logo_path"), *LOGO_HEADER)
    head = Table([[Paragraph(_esc(club.get("club_name")), club_s), logo or ""]],
                 colWidths=[width - LOGO_HEADER[0], LOGO_HEADER[0]])
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                              ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                              ("LINEBELOW", (0, 0), (-1, 0), 1, primary),
                              ("BOTTOMPADDING", (0, 0), (-1, 0), 8)]))
    story = [head, Spacer(1, 6 * mm), Paragraph("Turnierregeln", title_s), Spacer(1, 2 * mm)]

    t = ts.get_tournament(tournament_id) if tournament_id else None
    if t is not None:
        info = [t.name, german_date(t.date), t.location, t.organizer and f"Veranstalter: {t.organizer}"]
        story += [Paragraph(_esc(" · ".join(i for i in info if i)), sub_s)]
    story.append(Spacer(1, 6 * mm))
    for para in [p for p in (settings.get(ss.KEY_TOURNAMENT_RULES_TEXT) or "").split("\n\n") if p.strip()]:
        story += [Paragraph(_esc(para.strip()), body), Spacer(1, 2 * mm)]

    doc = SimpleDocTemplate(str(path), pagesize=pagesize,
                            leftMargin=tpl.MARGIN_LEFT, rightMargin=tpl.MARGIN_RIGHT,
                            topMargin=tpl.MARGIN_TOP, bottomMargin=tpl.MARGIN_BOTTOM,
                            title="Turnierregeln",
                            author=club.get("club_name") or "BowTally", creator="BowTally")
    doc.build(story, onFirstPage=footer, onLaterPages=footer,
              canvasmaker=tpl.WatermarkCanvas)
    return path