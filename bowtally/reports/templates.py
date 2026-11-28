# -*- coding: utf-8 -*-
"""Layout constants and font resolution for the reportlab result list."""
import os
from datetime import datetime
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
FOOTER_TEXT = "Erstellt am:"   # bottom left, followed by the timestamp

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
                # <i> in paragraphs needs the italic faces; without files they stay upright
                italic, bold_italic = _italic_files(reg, bold or reg)
                pdfmetrics.registerFont(TTFont(name + "-Italic", str(italic)))
                pdfmetrics.registerFont(TTFont(name + "-BoldItalic", str(bold_italic)))
                pdfmetrics.registerFontFamily(name, normal=name, bold=name + "-Bold",
                                              italic=name + "-Italic",
                                              boldItalic=name + "-BoldItalic")
                return name, name + "-Bold"
            except Exception:   # broken / unsupported font file -> try next
                continue
    return FALLBACK_FONT, FALLBACK_FONT_BOLD


_ITALIC = {"segoeui.ttf": ("segoeuii.ttf", "segoeuiz.ttf"), "arial.ttf": ("ariali.ttf", "arialbi.ttf"),
           "calibri.ttf": ("calibrii.ttf", "calibriz.ttf"), "verdana.ttf": ("verdanai.ttf", "verdanaz.ttf")}


def _italic_files(reg: Path, bold: Path) -> tuple[Path, Path]:
    """Italic and bold-italic file next to the regular one, else the upright faces."""
    names = _ITALIC.get(reg.name.lower()) or (
        reg.name.replace("-Regular", "").replace(".ttf", "-Italic.ttf"),
        bold.name.replace("-Bold", "").replace(".ttf", "-BoldItalic.ttf"))
    italic, bold_italic = reg.with_name(names[0]), bold.with_name(names[1])
    return (italic if italic.is_file() else reg), (bold_italic if bold_italic.is_file() else bold)


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


def draw_footer(c, created: str) -> None:
    """Same footer on every print: "Erstellt am: <timestamp>" left, page number centered."""
    from bowtally.services import settings_service as ss
    font = register_fonts([ss.get(ss.KEY_FONT_FAMILY) or "Open Sans", "Segoe UI", "Arial"])[0]
    c.saveState()
    c.setFont(font, FONT_SIZE_FOOTER)
    c.setFillColor(colors.HexColor(ss.get(ss.KEY_PRINT_COLOR_TEXT_SECONDARY) or "#777777"))
    y = MARGIN_BOTTOM / 2
    c.drawString(MARGIN_LEFT, y, f"{FOOTER_TEXT} {created}")
    c.drawCentredString(c._pagesize[0] / 2, y, f"Seite {c.getPageNumber()}")
    c.restoreState()


class WatermarkCanvas(rl_canvas.Canvas):
    """Canvas for every print (use as canvasmaker): footer and BowTally watermark on each page."""
    watermark_inset = (6 * mm, 4 * mm)        # right, bottom
    show_footer = True                        # certificates: watermark only

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._created = datetime.now().strftime("%d.%m.%Y %H:%M")

    def showPage(self):
        if self.show_footer:
            draw_footer(self, self._created)
        draw_watermark(self, *self.watermark_inset)
        super().showPage()
