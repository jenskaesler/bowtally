# -*- coding: utf-8 -*-
"""Central mailto helper: build and open mailto URLs from app_settings templates."""
import base64
import mimetypes
from pathlib import Path
from urllib.parse import quote

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

from bowtally.services import settings_service as ss
from bowtally.ui.components.toast import Toast


class _SafeDict(dict):
    """format_map helper that leaves unknown placeholders intact."""
    def __missing__(self, key):
        return "{" + key + "}"


def tournament_ctx(t, p=None) -> dict:
    """Build extra email context from tournament and optionally a participant."""
    ctx = {
        "ort": t.location or "",
        "iban": t.bank_iban or "",
        "anmeldefrist": f"{t.registration_deadline:%d.%m.%Y}" if t.registration_deadline else "",
        "checkin_start_time": t.checkin_start_time or "",
        "shooting_start_time": t.shooting_start_time or "",
        "bank_account_holder": t.bank_account_holder or "",
    }
    if p is not None:
        name = f"{p.archer.first_name} {p.archer.last_name}"
        cls = p.bow_class.name if p.bow_class else ""
        ref = (t.bank_reference_template or "").replace("{name}", name).replace(
            "{bow_class}", cls)
        ctx.update({
            "name": name,
            "first_name": p.archer.first_name or "",
            "last_name": p.archer.last_name or "",
            "startnummer": str(p.start_number) if p.start_number else "",
            "startgruppe": p.start_group or "",
            "startzeit": p.start_time or "",
            "verwendungszweck": ref,
        })
    return ctx


def _logo_data_uri(path: str | None) -> str:
    """Return the club logo as a data: URI, or "" if unset/unreadable."""
    if not path:
        return ""
    p = Path(path)
    if not p.is_file():
        return ""
    mime = mimetypes.guess_type(p.name)[0] or "image/png"
    try:
        return f"data:{mime};base64,{base64.b64encode(p.read_bytes()).decode('ascii')}"
    except OSError:
        return ""


def open_mailto(template_key: str, recipient_email: str | None, context: dict,
                parent=None) -> None:
    """Open a mailto: URL built from app_settings template `template_key`.

    Loads `{template_key}_subject` and `{template_key}_body` from settings,
    replaces placeholders from `context`, and opens the system mail client.
    Shows warning toasts for missing email or unconfigured template.
    """
    if not recipient_email:
        name = context.get("name") or context.get("first_name") or "Teilnehmer"
        Toast.show(parent, f"Keine E-Mail-Adresse für {name} hinterlegt", Toast.WARNING)
        return
    subj_raw = ss.get(f"{template_key}_subject")
    body_raw = ss.get(f"{template_key}_body")
    if not subj_raw and not body_raw:
        Toast.show(parent,
                   f"E-Mail-Vorlage \"{template_key}\" nicht konfiguriert. "
                   "Bitte unter Einstellungen > E-Mail-Vorlagen prüfen.",
                   Toast.WARNING)
        return
    profile = ss.get_club_profile()
    contact = " ".join(filter(None, [profile.get("first_board_fname"),
                                     profile.get("first_board_lname")]))
    full_name = context.get("name") or " ".join(
        filter(None, [context.get("first_name"), context.get("last_name")]))
    ctx = _SafeDict({
        "name": full_name,
        "first_name": context.get("first_name", ""),
        "last_name": context.get("last_name", ""),
        "vereinsname": profile.get("club_name") or "",
        "kontakt_name": contact,
        "kontakt_email": profile.get("email") or "",
        "kontakt_telefon": profile.get("phone") or "",
        "logo": _logo_data_uri(profile.get("logo_path")),
        **context,
    })
    subj = (subj_raw or "").format_map(ctx)
    body = (body_raw or "").format_map(ctx)
    url = f"mailto:{quote(recipient_email)}?subject={quote(subj)}&body={quote(body)}"
    QDesktopServices.openUrl(QUrl(url))