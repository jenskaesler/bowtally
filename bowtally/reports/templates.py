# -*- coding: utf-8 -*-
"""Layout constants and font resolution for the reportlab result list."""
import os
from pathlib import Path

from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A3, A4, A5, LETTER, landscape, portrait
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as rl_canvas

from bowtally import config

PAGE_SIZES = {"A4": A4, "A5": A5, "A3": A3, "LETTER": LETTER}

MARGIN_LEFT = 15 * mm
MARGIN_RIGHT = 15 * mm
MARGIN_TOP = 18 * mm
MARGIN_BOTTOM = 18 * mm

LOGO_MAX_WIDTH = 60 * mm
LOGO_MAX_HEIGHT = 40 * mm

FONT_SIZE_TITLE = 22
FONT_SIZE_SUBTITLE = 14
FONT_SIZE_HEADING = 15
FONT_SIZE_BODY = 10
FONT_SIZE_TABLE = 8.5
FONT_SIZE_FOOTER = 8

TABLE_ROW_PADDING = 3
PODIUM_PLACES = 3
FOOTER_TEXT = "Erstellt mit BowTally"

FALLBACK_FONT = "Helvetica"
FALLBACK_FONT_BOLD = "Helvetica-Bold"

_FONT_DIRS = [Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts",
              Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Windows" / "Fonts"]

# Well known file names that do not follow the <Family>-Regular.ttf pattern
_KNOWN = {
    "segoe ui": ("segoeui.ttf", "segoeuib.ttf"),
    "arial": ("arial.ttf", "arialbd.ttf"),
    "calibri": ("calibri.ttf", "calibrib.ttf"),
    "verdana": ("verdana.ttf", "verdanab.ttf"),
    "tahoma": ("tahoma.ttf", "tahomabd.ttf"),
}


def page_size(name: str, orientation: str):
    size = PAGE_SIZES.get((name or "A4").upper(), A4)
    return landscape(size) if orientation == "landscape" else portrait(size)


def _find(filename: str) -> Path | None:
    for d in _FONT_DIRS:
        p = d / filename
        if p.is_file():
            return p
    return None


def _candidates(family: str) -> list[tuple[str, str]]:
    compact = family.replace(" ", "")
    out = [(f"{compact}-Regular.ttf", f"{compact}-Bold.ttf"), (f"{compact}.ttf",
                                                                  f"{compact}-Bold.ttf")]
    if family.lower() in _KNOWN:
        out.insert(0, _KNOWN[family.lower()])
    return out


def _bundled(family: str) -> tuple[Path, Path] | None:
    files = config.BUNDLED_FONTS.get(family)
    return tuple(config.FONTS_DIR / name for name in files) if files else None


def register_fonts(families: list[str]) -> tuple[str, str]:
    """Register the first available TTF family (bundled, then installed). Returns (regular, bold)."""
    for family in families:
        bundled = _bundled(family)
        candidates = [bundled] if bundled else []
        for reg_file, bold_file in _candidates(family):
            candidates.append((_find(reg_file), _find(bold_file)))
        for reg, bold in candidates:
            if reg is None:
                continue
            name = family.replace(" ", "")
            try:
                pdfmetrics.registerFont(TTFont(name, str(reg)))
                pdfmetrics.registerFont(TTFont(name + "-Bold", str(bold or reg)))
                return name, name + "-Bold"
            except Exception:   # broken / unsupported font file -> try next
                continue
    return FALLBACK_FONT, FALLBACK_FONT_BOLD


# ------------------------------------------------------------------ watermark

REPO_URL = "https://github.com/jenskaesler/bowtally"
WATERMARK_TEXT = "sponsored by BowTally"
WATERMARK_LOGO = config.ASSETS_DIR / "icon_140x140.png"
WATERMARK_QR = 12 * mm
WATERMARK_LOGO_SIZE = 6 * mm


def _qr_drawing(size: float) -> Drawing:
    widget = QrCodeWidget(REPO_URL, barBorder=0)
    x0, y0, x1, y1 = widget.getBounds()
    d = Drawing(size, size, transform=[size / (x1 - x0), 0, 0, size / (y1 - y0), 0, 0])
    d.add(widget)
    return d


def draw_watermark(c, right: float = 6 * mm, bottom: float = 4 * mm) -> None:
    """Bottom right: BowTally logo, "sponsored by BowTally" and a QR code to the repository."""
    page_w = c._pagesize[0]
    qr_x = page_w - right - WATERMARK_QR
    c.saveState()
    renderPDF.draw(_qr_drawing(WATERMARK_QR), c, qr_x, bottom)
    mid = bottom + WATERMARK_QR / 2
    c.setFont(FALLBACK_FONT, 6.5)
    c.setFillColor(colors.HexColor("#777777"))
    text_right = qr_x - 1.5 * mm
    c.drawRightString(text_right, mid - 2.2, WATERMARK_TEXT)
    text_w = pdfmetrics.stringWidth(WATERMARK_TEXT, FALLBACK_FONT, 6.5)
    try:
        c.drawImage(ImageReader(str(WATERMARK_LOGO)),
                    text_right - text_w - 1.5 * mm - WATERMARK_LOGO_SIZE,
                    mid - WATERMARK_LOGO_SIZE / 2, WATERMARK_LOGO_SIZE, WATERMARK_LOGO_SIZE,
                    mask="auto")
    except Exception:      # missing asset: watermark without logo
        pass
    c.linkURL(REPO_URL, (text_right - text_w, bottom, page_w - right, bottom + WATERMARK_QR))
    c.restoreState()


class WatermarkCanvas(rl_canvas.Canvas):
    """Canvas that puts the BowTally watermark on every page (use as canvasmaker)."""
    watermark_inset = (6 * mm, 4 * mm)        # right, bottom

    def showPage(self):
        draw_watermark(self, *self.watermark_inset)
        super().showPage()
