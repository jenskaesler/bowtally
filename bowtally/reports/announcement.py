# -*- coding: utf-8 -*-
"""Tournament announcement (Ausschreibung) as PDF.

All content comes from the database (tournament, club profile, app_settings text templates);
only section headings and the layout live in code.
"""
import logging
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (Image, KeepTogether, ListFlowable, ListItem, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

from bowtally import config
from bowtally.reports import templates as tpl
from bowtally.services import settings_service as ss
from bowtally.services import tournament_service as ts

log = logging.getLogger(__name__)

WEEKDAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
MONTHS = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September",
          "Oktober", "November", "Dezember"]
# readable labels for placeholders in the bank reference template
REFERENCE_PLACEHOLDERS = {"{name}": "Name", "{bow_class}": "Bogenklasse",
                          "{first_name}": "Vorname", "{last_name}": "Nachname"}
HEADINGS = {
    "title": "Einladung zum {name}",
    "schedule": "Termin und Ablauf",
    "course": "Der Parcours",
    "classes": "Bogen- und Wettkampfklassen",
    "fees": "Startgeld",
    "payment": "Anmeldung und Überweisung",
    "contact": "Anmeldung und Kontakt",
    "notes": "Wichtige Hinweise",
}
LOGO_HEADER = (45 * mm, 28 * mm)
LOGO_FOOTER = (25 * mm, 16 * mm)


def german_date(d) -> str:
    return f"{WEEKDAYS[d.weekday()]}, {d.day}. {MONTHS[d.month - 1]} {d.year}"


def split_info(text: str | None) -> tuple[str, str]:
    """additional_info: first paragraph = introduction, the rest = closing text."""
    parts = [p.strip() for p in (text or "").replace("\r\n", "\n").split("\n\n") if p.strip()]
    return (parts[0] if parts else ""), "\n\n".join(parts[1:])


def readable_reference(template: str | None) -> str:
    text = template or ""
    for placeholder, label in REFERENCE_PLACEHOLDERS.items():
        text = text.replace(placeholder, label)
    return text


def _esc(text) -> str:
    return (str(text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace("\n", "<br/>"))


def _logo(path, max_w, max_h):
    if not path or not Path(path).is_file():
        return None
    try:
        img = Image(path)
        ratio = min(max_w / img.imageWidth, max_h / img.imageHeight)
        img.drawWidth, img.drawHeight = img.imageWidth * ratio, img.imageHeight * ratio
        return img
    except Exception as exc:   # unreadable image must not block the document
        log.error("Logo konnte nicht geladen werden (%s): %s", path, exc)
        return None


def announcement_path(tournament_id: int) -> Path:
    return config.export_dir() / f"announcement_{tournament_id}_{datetime.now():%Y%m%d_%H%M%S}.pdf"


def generate_announcement_pdf(tournament_id: int, path: str | Path | None = None) -> Path:
    t = ts.get_tournament(tournament_id)
    path = Path(path) if path else announcement_path(tournament_id)
    settings = ss.get_all()
    club = ss.get_club_profile()
    primary = colors.HexColor(settings.get(ss.KEY_COLOR_PRIMARY) or "#00357D")
    border = colors.HexColor(settings.get(ss.KEY_COLOR_BORDER) or "#D0D7E0")
    muted = colors.HexColor(settings.get(ss.KEY_COLOR_TEXT_SECONDARY) or "#777777")
    font, bold = tpl.register_fonts([settings.get(ss.KEY_FONT_FAMILY) or "Open Sans",
                                     "Segoe UI", "Arial"])
    base = ParagraphStyle("base", fontName=font, fontSize=10.5, leading=15)
    st = {
        "club": ParagraphStyle("club", base, fontName=bold, fontSize=16, leading=20),
        "title": ParagraphStyle("title", base, fontName=bold, fontSize=21, leading=26,
                                textColor=primary, spaceBefore=6),
        "subtitle": ParagraphStyle("subtitle", base, textColor=muted, spaceAfter=6),
        "h": ParagraphStyle("h", base, fontName=bold, fontSize=13, leading=17,
                            textColor=primary, spaceBefore=12, spaceAfter=4),
        "p": base,
        "strong": ParagraphStyle("strong", base, fontName=bold),
        "sign": ParagraphStyle("sign", base, fontName=bold, spaceBefore=10),
    }
    width = tpl.page_size("A4", "portrait")[0] - tpl.MARGIN_LEFT - tpl.MARGIN_RIGHT

    def section(key, *flowables):
        return [KeepTogether([Paragraph(HEADINGS[key], st["h"]), *flowables])]

    def lines(*items):
        return [Paragraph(_esc(i), st["p"]) for i in items if i]

    story = []
    # header: club name left, logo right, rule
    logo = _logo(club.get("logo_path"), *LOGO_HEADER)
    head = Table([[Paragraph(_esc(club.get("club_name") or ""), st["club"]), logo or ""]],
                 colWidths=[width - LOGO_HEADER[0], LOGO_HEADER[0]])
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                              ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                              ("LINEBELOW", (0, 0), (-1, 0), 1, primary),
                              ("BOTTOMPADDING", (0, 0), (-1, 0), 8)]))
    story += [head, Spacer(1, 8 * mm)]

    story.append(Paragraph(_esc(HEADINGS["title"].format(name=t.name)), st["title"]))
    class_names = ", ".join(f"{bc.name} ({bc.abbreviation})" if bc.abbreviation else bc.name
                            for bc in t.bow_classes)
    story.append(Paragraph(_esc(class_names), st["subtitle"]))
    intro, closing = split_info(t.additional_info)
    if intro:
        story += [Spacer(1, 3 * mm), Paragraph(_esc(intro), st["p"])]

    schedule = [german_date(t.date)]
    if t.checkin_start_time:
        schedule.append(f"Einschreibung: ab {t.checkin_start_time} Uhr")
    if t.practice_allowed:
        schedule.append("Einschießen: nach dem Einschreiben"
                        + (f" auf {t.practice_location}" if t.practice_location else "")
                        + " möglich")
    if t.shooting_start_time:
        schedule.append(f"Schießbeginn: {t.shooting_start_time} Uhr")
    if t.location:
        schedule.append(f"Austragungsort: {t.location}")
    story += section("schedule", *lines(*schedule))

    rule = t.scoring_rule
    scoring = ", ".join(f"{z['zone']} {z['points']}" for z in rule.ring_values) if rule else ""
    course = [f"{t.num_targets} × 3D-Ziele"
              + (f", {t.shots_per_target} Pfeile je Ziel" if t.shots_per_target > 1 else "")]
    if rule:
        course.append(f"Wertung ({rule.name}): {scoring}")
    course.append(t.notes)
    story += section("course", *lines(*course))

    class_items = ListFlowable(
        [ListItem(Paragraph(_esc(f"{bc.name} ({bc.abbreviation})" if bc.abbreviation
                                 else bc.name), st["p"]), leftIndent=12) for bc in t.bow_classes],
        bulletType="bullet", start="•", leftIndent=12)
    story += section("classes", class_items,
                     *lines(settings.get("announcement_group_hint")))

    if t.fees:
        fee_table = Table([[Paragraph(_esc(f.name), st["p"]),
                            Paragraph(f"{f.amount:.2f} €".replace(".", ","), st["strong"])]
                           for f in t.fees], colWidths=[width * 0.6, width * 0.25],
                          hAlign="LEFT")
        fee_table.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.4, border),
                                       ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                                       ("TOPPADDING", (0, 0), (-1, -1), 4),
                                       ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
        story += section("fees", fee_table)

    payment = []
    if t.registration_deadline:
        payment.append(Paragraph(_esc(
            "Die Anmeldung erfolgt per E-Mail bis spätestens "
            f"{german_date(t.registration_deadline)}."), st["p"]))
    if t.max_participants:
        payment.append(Paragraph(_esc(f"Die Teilnehmerzahl ist auf {t.max_participants} "
                                      "Personen begrenzt!"), st["strong"]))
    bank = [(k, v) for k, v in (("Kontoinhaber", t.bank_account_holder), ("IBAN", t.bank_iban),
                                ("BIC", t.bank_bic),
                                ("Verwendungszweck", readable_reference(
                                    t.bank_reference_template))) if v]
    if bank:
        bank_table = Table([[Paragraph(_esc(k), st["p"]), Paragraph(_esc(v), st["strong"])]
                            for k, v in bank], colWidths=[40 * mm, width - 40 * mm],
                           hAlign="LEFT")
        bank_table.setStyle(TableStyle([("TOPPADDING", (0, 0), (-1, -1), 2),
                                        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                                        ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
        payment += [Spacer(1, 2 * mm), bank_table]
    payment += lines(settings.get("announcement_payment_hint"))
    if payment:
        story += section("payment", *payment)

    contact = [v for v in (t.contact_name, t.contact_phone and f"Telefon: {t.contact_phone}",
                           t.contact_email and f"E-Mail: {t.contact_email}") if v]
    if contact:
        story += section("contact", *lines(*contact))

    notes = [n.strip() for n in (t.legal_notes or "").splitlines() if n.strip()]
    if notes:
        story += section("notes", ListFlowable(
            [ListItem(Paragraph(_esc(n), st["p"]), leftIndent=12) for n in notes],
            bulletType="bullet", start="•", leftIndent=12))

    if closing:
        story += [Spacer(1, 6 * mm), Paragraph(_esc(closing), st["p"])]
    if club.get("club_name"):
        story.append(Paragraph(_esc(club["club_name"]), st["sign"]))
    if ss.get_bool("print_show_logo"):
        small = _logo(club.get("logo_path"), *LOGO_FOOTER)
        if small is not None:
            small.hAlign = "LEFT"
            story += [Spacer(1, 3 * mm), small]

    doc = SimpleDocTemplate(str(path), pagesize=tpl.page_size("A4", "portrait"),
                            leftMargin=tpl.MARGIN_LEFT, rightMargin=tpl.MARGIN_RIGHT,
                            topMargin=tpl.MARGIN_TOP, bottomMargin=tpl.MARGIN_BOTTOM,
                            title=HEADINGS["title"].format(name=t.name),
                            author=club.get("club_name") or "BowTally", creator="BowTally")
    doc.build(story)
    ts.mark_announcement_generated(tournament_id)
    log.info("Ausschreibung erstellt: %s", path)
    return path
