# -*- coding: utf-8 -*-
"""Layout constants and font resolution for the reportlab result list."""
import os
from pathlib import Path

from reportlab.lib.pagesizes import A3, A4, A5, LETTER, landscape, portrait
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

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
