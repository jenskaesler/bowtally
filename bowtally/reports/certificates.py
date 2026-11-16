# -*- coding: utf-8 -*-
"""Urkunden-PDF: genau eine A4-Seite pro Platzierung (Podium) mit Rahmen, Logo und Siegel."""
import re
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from bowtally import config
from bowtally.reports import templates as tpl
from bowtally.services import ranking_service as rs
from bowtally.services import settings_service as ss
from bowtally.services.tournament_service import get_tournament

KEY_CERT_BG = "cert_background_color"
MEDALS = {1: "#C9A227", 2: "#9AA0A6", 3: "#B0693A"}   # Gold, Silber, Bronze
PAGE_W, PAGE_H = tpl.page_size("A4", "portrait")
TEXT_W = PAGE_W - 56 * mm          # Textbreite innerhalb des Rahmens


def _path(tournament_id: int) -> Path:
    t = get_tournament(tournament_id)
    safe = re.sub(r"[^\w-]+", "_", t.name).strip("_") or "Turnier"
    return config.export_dir() / f"Urkunden_{safe}_{datetime.now():%Y%m%d_%H%M%S}.pdf"


def _text(c, text, y, font, size, color, spacing=0.0):
    """Centered single line; shrinks the font until it fits, optional letter spacing."""
    while size > 8 and stringWidth(text, font, size) + spacing * len(text) > TEXT_W:
        size -= 0.5
    width = stringWidth(text, font, size) + spacing * (len(text) - 1)
    t = c.beginText(PAGE_W / 2 - width / 2, y)
    t.setFont(font, size)
    t.setFillColor(color)
    t.setCharSpace(spacing)
    t.textOut(text)
    c.drawText(t)


def _divider(c, y, color):
    """Thin line with a small diamond in the middle."""
    c.setStrokeColor(color)
    c.setLineWidth(0.8)
    half = 38 * mm
    c.line(PAGE_W / 2 - half, y, PAGE_W / 2 - 4 * mm, y)
    c.line(PAGE_W / 2 + 4 * mm, y, PAGE_W / 2 + half, y)
    c.setFillColor(color)
    p = c.beginPath()
    p.moveTo(PAGE_W / 2, y + 2 * mm)
    p.lineTo(PAGE_W / 2 + 2 * mm, y)
    p.lineTo(PAGE_W / 2, y - 2 * mm)
    p.lineTo(PAGE_W / 2 - 2 * mm, y)
    p.close()
    c.drawPath(p, fill=1, stroke=0)


def _frame(c, color):
    outer, inner = 10 * mm, 14 * mm
    c.setStrokeColor(color)
    c.setLineWidth(2.5)
    c.rect(outer, outer, PAGE_W - 2 * outer, PAGE_H - 2 * outer)
    c.setLineWidth(0.7)
    c.rect(inner, inner, PAGE_W - 2 * inner, PAGE_H - 2 * inner)
    c.setFillColor(color)
    for x in (outer, PAGE_W - outer):          # Eckquadrate
        for y in (outer, PAGE_H - outer):
            c.rect(x - 2.5 * mm, y - 2.5 * mm, 5 * mm, 5 * mm, fill=1, stroke=0)


def _seal(c, cx, cy, rank, bold_font, fallback):
    """Medal-like rosette with the place number."""
    color = colors.HexColor(MEDALS.get(rank, fallback))
    c.setFillColor(color)
    c.circle(cx, cy, 19 * mm, fill=1, stroke=0)
    c.setStrokeColor(colors.white)
    c.setLineWidth(1.2)
    c.circle(cx, cy, 16 * mm, fill=0, stroke=1)
    c.setFillColor(colors.white)
    c.setFont(bold_font, 44)
    c.drawCentredString(cx, cy - 7 * mm, str(rank))


def _logo(c, path, y_top):
    """Draw the club logo centered below y_top; returns the y below it."""
    try:
        img = ImageReader(path)
        w, h = img.getSize()
        scale = min(45 * mm / w, 24 * mm / h)
        c.drawImage(img, PAGE_W / 2 - w * scale / 2, y_top - h * scale, w * scale, h * scale,
                    mask="auto")
        return y_top - h * scale
    except Exception:       # missing/unreadable logo: certificate without logo
        return y_top


def build_certificates(tournament_id: int, path: str | Path | None = None) -> Path:
    """Generate one A4 certificate per podium place and class."""
    path = Path(path) if path else _path(tournament_id)
    t = get_tournament(tournament_id)
    per_class = rs.compute_ranking(tournament_id)
    bow_classes = {bc.id: bc for bc in t.bow_classes}
    settings = ss.get_all()
    profile = ss.get_club_profile()
    font, bold = tpl.register_fonts([settings.get(ss.KEY_FONT_FAMILY) or "Open Sans",
                                     "Segoe UI", "Arial"])
    primary = colors.HexColor(settings.get(ss.KEY_COLOR_PRIMARY) or "#00357D")
    bg = settings.get(KEY_CERT_BG) or "#FFFFFF"
    board = " ".join(filter(None, [profile.get("first_board_fname"),
                                   profile.get("first_board_lname")]))
    place_date = ", ".join(filter(None, [t.location, f"{t.date:%d.%m.%Y}"]))

    c = canvas.Canvas(str(path), pagesize=(PAGE_W, PAGE_H))
    c.setTitle(f"Urkunden {t.name}")
    count = 0
    for bc_id, rows in per_class.items():
        bc = bow_classes.get(bc_id)
        for entry in rows[:tpl.PODIUM_PLACES]:
            count += 1
            if bg.upper() != "#FFFFFF":
                c.setFillColor(colors.HexColor(bg))
                c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
            _frame(c, primary)
            y = PAGE_H - 26 * mm
            if profile.get("logo_path"):
                y = _logo(c, profile["logo_path"], y) - 6 * mm
            if profile.get("club_name"):
                _text(c, profile["club_name"].upper(), y - 4 * mm, font, 12, colors.grey, 2)
                y -= 10 * mm
            _text(c, "URKUNDE", y - 22 * mm, bold, 50, primary, 6)
            _divider(c, y - 31 * mm, primary)
            _text(c, "für hervorragende Leistungen verliehen an", y - 46 * mm, font, 13,
                  colors.black)
            _text(c, entry.name, y - 62 * mm, bold, 32, primary)
            _seal(c, PAGE_W / 2, y - 98 * mm, entry.rank, bold, settings.get(
                ss.KEY_COLOR_PRIMARY) or "#00357D")
            _text(c, f"{entry.rank}. Platz", y - 127 * mm, bold, 24, colors.black)
            if bc:
                _text(c, f"Klasse: {bc.name}", y - 137 * mm, font, 15, colors.black)
            _text(c, f"{entry.total} Punkte", y - 146 * mm, font, 14, colors.black)
            line_y = y - 160 * mm
            for i, line in enumerate(simpleSplit(f"beim Turnier „{t.name}“", bold, 17, TEXT_W)):
                _text(c, line, line_y - i * 8 * mm, bold, 17, colors.black)
            # Fußbereich: Ort/Datum links, Unterschrift rechts
            base = 34 * mm
            c.setStrokeColor(colors.black)
            c.setLineWidth(0.5)
            c.line(28 * mm, base, 83 * mm, base)
            c.line(PAGE_W - 83 * mm, base, PAGE_W - 28 * mm, base)
            c.setFillColor(colors.black)
            c.setFont(font, 10)
            c.drawCentredString(55.5 * mm, base - 5 * mm, place_date)
            c.drawCentredString(PAGE_W - 55.5 * mm, base - 5 * mm,
                                board or "Unterschrift")
            if board:
                c.setFont(font, 8)
                c.drawCentredString(PAGE_W - 55.5 * mm, base - 9.5 * mm, "Vorstand")
            c.showPage()
    if not count:
        c.setFont(font, 12)
        c.drawString(30 * mm, PAGE_H - 40 * mm, "Keine Ranglisten-Einträge vorhanden.")
        c.showPage()
    c.save()
    return path
