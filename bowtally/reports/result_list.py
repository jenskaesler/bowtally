# -*- coding: utf-8 -*-
"""Print-ready result list as PDF (cover page + one ranking page per bow class)."""
import logging
import re
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

from bowtally import config
from bowtally.reports import templates as tpl
from bowtally.services import ranking_service, settings_service as ss
from bowtally.services.scoring_service import COUNTER_KEYS, active_specials
from bowtally.services.tournament_service import get_tournament

log = logging.getLogger(__name__)

MIN_TARGET_COL = 6.5 * mm


def _styles(font: str, bold: str, primary, secondary_text) -> dict[str, ParagraphStyle]:
    base = ParagraphStyle("base", fontName=font, fontSize=tpl.FONT_SIZE_BODY, leading=13)
    return {
        "title": ParagraphStyle("title", base, fontName=bold, fontSize=tpl.FONT_SIZE_TITLE,
                                leading=28, alignment=TA_CENTER, textColor=primary),
        "subtitle": ParagraphStyle("subtitle", base, fontSize=tpl.FONT_SIZE_SUBTITLE,
                                   leading=18, alignment=TA_CENTER),
        "center": ParagraphStyle("center", base, alignment=TA_CENTER),
        "muted": ParagraphStyle("muted", base, alignment=TA_CENTER, textColor=secondary_text),
        "heading": ParagraphStyle("heading", base, fontName=bold,
                                  fontSize=tpl.FONT_SIZE_HEADING, leading=20,
                                  textColor=primary, spaceAfter=6),
        "cell": ParagraphStyle("cell", base, fontSize=tpl.FONT_SIZE_TABLE,
                               leading=tpl.FONT_SIZE_TABLE + 2),
        "cell_podium": ParagraphStyle("cell_podium", base, fontName=bold,
                                      fontSize=tpl.FONT_SIZE_TABLE,
                                      leading=tpl.FONT_SIZE_TABLE + 2, textColor=colors.white),
    }


def _esc(text) -> str:
    return (str(text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _logo(path: str | None):
    if not path or not Path(path).is_file():
        return None
    try:
        img = Image(path)
        ratio = min(tpl.LOGO_MAX_WIDTH / img.imageWidth, tpl.LOGO_MAX_HEIGHT / img.imageHeight)
        img.drawWidth, img.drawHeight = img.imageWidth * ratio, img.imageHeight * ratio
        return img
    except Exception as exc:  # unreadable image must not block the report
        log.error("Logo konnte nicht geladen werden (%s): %s", path, exc)
        return None


def build_result_list(tournament_id: int, path: str | Path) -> Path:
    path = Path(path)
    t = get_tournament(tournament_id)
    settings = ss.get_all()
    club = ss.get_club_profile()
    primary = colors.HexColor(settings.get(ss.KEY_PRINT_COLOR_PRIMARY) or "#00357D")
    secondary = colors.HexColor(settings.get(ss.KEY_PRINT_COLOR_SECONDARY) or "#0258CF")
    text2 = colors.HexColor(settings.get(ss.KEY_PRINT_COLOR_TEXT_SECONDARY) or "#777777")
    border = colors.HexColor(settings.get(ss.KEY_PRINT_COLOR_BORDER) or "#D0D7E0")
    show_logo = ss.get_bool(ss.KEY_PRINT_SHOW_LOGO)
    show_targets = ss.get_bool(ss.KEY_PRINT_SHOW_SCORES_PER_TARGET)
    font, bold = tpl.register_fonts([settings.get(ss.KEY_FONT_FAMILY) or "Open Sans",
                                     "Segoe UI", "Arial"])
    st = _styles(font, bold, primary, text2)
    pagesize = tpl.page_size(settings.get(ss.KEY_PRINT_PAPER_SIZE),
                             settings.get(ss.KEY_PRINT_ORIENTATION) or "portrait")
    doc = SimpleDocTemplate(str(path), pagesize=pagesize, leftMargin=tpl.MARGIN_LEFT,
                            rightMargin=tpl.MARGIN_RIGHT, topMargin=tpl.MARGIN_TOP,
                            bottomMargin=tpl.MARGIN_BOTTOM, title=t.name,
                            author=club.get("club_name") or "BowTally", creator="BowTally")
    ranking = ranking_service.compute_ranking(tournament_id)
    class_names = {bc.id: bc.name for bc in t.bow_classes}
    tracked_spec = [sp for sp in active_specials(t.scoring_rule) if sp.get("track")]

    # ---- cover page
    story = [Spacer(1, 15 * mm)]
    logo = _logo(club.get("logo_path")) if show_logo else None
    if logo is not None:
        story += [logo, Spacer(1, 8 * mm)]
    if club.get("club_name"):
        story += [Paragraph(_esc(club["club_name"]), st["subtitle"]), Spacer(1, 10 * mm)]
    story += [Paragraph(_esc(t.name), st["title"]), Spacer(1, 4 * mm),
              Paragraph("Ergebnisliste", st["subtitle"]), Spacer(1, 12 * mm)]
    classes_with_people = [cid for cid, rows in ranking.items() if rows]
    info = [("Datum", t.date.strftime("%d.%m.%Y")), ("Ort", t.location),
            ("Veranstalter", t.organizer), ("Regelwerk", t.scoring_rule.name
                                            if t.scoring_rule else "-"),
            ("Teilnehmer", str(len(t.participants))),
            ("Klassen", str(len(classes_with_people))),
            ("Scheiben", f"{t.num_targets} × {t.shots_per_target} Schuss")]
    info_table = Table([[Paragraph(f"<b>{k}</b>", st["cell"]), Paragraph(_esc(v), st["cell"])]
                        for k, v in info if v], colWidths=[40 * mm, 80 * mm])
    info_table.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), font),
                                    ("LINEBELOW", (0, 0), (-1, -1), 0.4, border),
                                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    story.append(info_table)

    # ---- one page per class
    width = pagesize[0] - tpl.MARGIN_LEFT - tpl.MARGIN_RIGHT
    scoring_mode = getattr(t, "scoring_mode", "per_target") or "per_target"
    num_rounds = getattr(t, "num_rounds", 1) or 1
    rounds = getattr(t, "rounds", []) or []
    round_labels = ([r.label for r in sorted(rounds, key=lambda r: r.round_number)]
                    if rounds else [f"{i}. Runde" for i in range(1, num_rounds + 1)])
    ties = ranking_service.podium_ties(tournament_id)
    show_shoot_off = ranking_service.has_shoot_off_values(ranking)
    for cid in classes_with_people:
        story += [PageBreak(),
                  Paragraph(_esc(class_names.get(cid, "Ohne Klasse")), st["heading"]),
                  _class_table(ranking[cid], t.num_targets, show_targets, width, st, font,
                               bold, primary, secondary, border,
                               scoring_mode=scoring_mode, round_labels=round_labels,
                               tracked_specials=tracked_spec, show_shoot_off=show_shoot_off)]
        class_ties = ranking_service.describe_ties([g for g in ties if g.class_id == cid])
        if class_ties:
            story += [Spacer(1, 4 * mm), Paragraph(_esc(class_ties), st["muted"])]
    if not classes_with_people:
        story += [PageBreak(), Paragraph("Keine Teilnehmer erfasst.", st["muted"])]

    doc.build(story, canvasmaker=tpl.WatermarkCanvas)
    log.info("Ergebnisliste erstellt: %s", path)
    return path


def _class_table(rows, num_targets, show_targets, width, st, font, bold, primary, secondary,
                 border, scoring_mode: str = "per_target",
                 round_labels: list | None = None,
                 tracked_specials: list | None = None,
                 show_shoot_off: bool = False) -> Table:
    fixed = {"rank": 11 * mm, "no": 12 * mm, "total": 15 * mm}
    rest = width - sum(fixed.values())
    spec_w = 12 * mm

    # per_round / total_only only know the active Kill / X counters; per_target all tracked specials
    specials = [sp for sp in (tracked_specials or [])
                if scoring_mode == "per_target" or sp.get("key") in COUNTER_KEYS]
    extra_headers = [sp["label"] for sp in specials] + (["Stechen"] if show_shoot_off else [])
    extra_widths = [spec_w] * len(extra_headers)
    rest -= spec_w * len(extra_headers)

    def extra_cells(r) -> list:
        cells = [str(r.specials.get(sp["key"]) or "") for sp in specials]
        if show_shoot_off:
            cells.append("" if r.shoot_off_entered is None else str(r.shoot_off_entered))
        return cells

    def build(header, widths, line_of, compact=False) -> Table:
        data = [header]
        style = _base_style(font, bold, secondary, border)
        if compact:
            style.append(("ALIGN", (4, 0), (4, -1), "LEFT"))
        for i, r in enumerate(rows, start=1):
            podium = r.rank <= tpl.PODIUM_PLACES and r.total > 0
            cell = st["cell_podium"] if podium else st["cell"]
            data.append([f"{r.rank}.", r.start_number or "", Paragraph(_esc(r.name), cell),
                         Paragraph(_esc(r.club), cell)] + line_of(r, cell) + extra_cells(r)
                        + [r.total])
            _add_podium_style(style, i, r.rank, r.total, primary, bold)
        table = Table(data, colWidths=widths, repeatRows=1)
        table.setStyle(TableStyle(style))
        return table

    head = ["Rang", "St.-Nr.", "Name", "Verein"]
    if scoring_mode == "total_only":
        name_w = rest * 0.55
        return build(head + extra_headers + ["Gesamt"],
                     [fixed["rank"], fixed["no"], name_w, rest - name_w] + extra_widths
                     + [fixed["total"]], lambda r, cell: [])

    if scoring_mode == "per_round":
        labels = round_labels or []
        n_rounds = len(labels)
        rnd_w = min((rest * 0.4) / max(n_rounds, 1), 20 * mm)
        name_w = (rest - rnd_w * n_rounds) * 0.55
        club_w = rest - rnd_w * n_rounds - name_w
        return build(head + labels + extra_headers + ["Gesamt"],
                     [fixed["rank"], fixed["no"], name_w, club_w] + [rnd_w] * n_rounds
                     + extra_widths + [fixed["total"]],
                     lambda r, cell: ["" if v is None else str(v) for v in (r.round_totals or [])])

    # per_target (default)
    target_w = 0
    compact = False
    if show_targets:
        target_w = (rest * 0.55) / num_targets
        if target_w < MIN_TARGET_COL:
            compact, target_w = True, 0
    name_w = (rest - target_w * num_targets) * (0.35 if compact else 0.55)
    club_w = (rest - target_w * num_targets) * (0.25 if compact else 0.45)
    header, widths = head, [fixed["rank"], fixed["no"], name_w, club_w]
    if show_targets and compact:
        header, widths = header + ["Einzelwertungen"], widths + [rest - name_w - club_w]
    elif show_targets:
        header = header + [str(i) for i in range(1, num_targets + 1)]
        widths = widths + [target_w] * num_targets

    def per_target_cells(r, cell) -> list:
        scores = ["" if v is None else str(v) for v in r.target_totals]
        if show_targets and compact:
            return [Paragraph(" ".join(sc or "–" for sc in scores), cell)]
        return scores if show_targets else []

    return build(header + extra_headers + ["Gesamt"], widths + extra_widths + [fixed["total"]],
                 per_target_cells, compact)


def _base_style(font, bold, secondary, border=None) -> list:
    line_color = border or secondary
    return [
        ("FONTNAME", (0, 0), (-1, -1), font),
        ("FONTSIZE", (0, 0), (-1, -1), tpl.FONT_SIZE_TABLE),
        ("FONTNAME", (0, 0), (-1, 0), bold),
        ("BACKGROUND", (0, 0), (-1, 0), secondary),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (1, -1), "RIGHT"),
        ("ALIGN", (4, 0), (-1, -1), "CENTER"),
        ("ALIGN", (-1, 0), (-1, -1), "RIGHT"),
        ("FONTNAME", (-1, 1), (-1, -1), bold),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, line_color),
        ("TOPPADDING", (0, 0), (-1, -1), tpl.TABLE_ROW_PADDING),
        ("BOTTOMPADDING", (0, 0), (-1, -1), tpl.TABLE_ROW_PADDING),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ]


def _add_podium_style(style, i, rank, total, primary, bold):
    if rank <= tpl.PODIUM_PLACES and total > 0:
        shade = {1: 1.0, 2: 0.8, 3: 0.62}.get(rank, 0.62)
        bg = colors.Color(primary.red, primary.green, primary.blue, alpha=shade)
        style += [("BACKGROUND", (0, i), (-1, i), bg),
                  ("TEXTCOLOR", (0, i), (-1, i), colors.white),
                  ("FONTNAME", (0, i), (-1, i), bold)]


def temp_pdf_path(tournament_id: int) -> Path:
    t = get_tournament(tournament_id)
    safe = re.sub(r"[^\w-]+", "_", t.name).strip("_") or "Turnier"
    return config.export_dir() / f"Ergebnisliste_{safe}_{datetime.now():%Y%m%d_%H%M%S}.pdf"
