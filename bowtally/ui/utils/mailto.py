# -*- coding: utf-8 -*-
"""Central mailto helper: build and open mailto URLs from app_settings templates."""
from urllib.parse import quote

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

from bowtally.services import settings_service as ss
from bowtally.ui.components.toast import Toast


class _SafeDict(dict):
    """format_map helper that leaves unknown placeholders intact."""
    def __missing__(self, key):
        return "{" + key + "}"


def open_mailto(template_key: str, recipient_email: str | None, context: dict,
                parent=None) -> None:
    """Open a mailto: URL built from app_settings template `template_key`.

    Loads `{template_key}_subject` and `{template_key}_body` from settings,
    replaces placeholders from `context`, and opens the system mail client.
    Shows warning toasts for missing email or unconfigured template.
    """
    if not recipient_email:
        name = context.get("name", "Teilnehmer")
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
    _contact = " ".join(filter(None, [profile.get("first_board_fname"),
                                      profile.get("first_board_lname")]))
    ctx = _SafeDict({
        "vereinsname": profile.get("club_name") or "",
        "kontakt_name": _contact,
        "kontakt_email": profile.get("email") or "",
        "kontakt_telefon": profile.get("phone") or "",
        **context,
    })
    subj = (subj_raw or "").format_map(ctx)
    body = (body_raw or "").format_map(ctx)
    url = f"mailto:{quote(recipient_email)}?subject={quote(subj)}&body={quote(body)}"
    QDesktopServices.openUrl(QUrl(url))
