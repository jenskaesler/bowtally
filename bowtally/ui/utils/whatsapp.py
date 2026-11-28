# -*- coding: utf-8 -*-
"""WhatsApp click-to-chat (https://wa.me): the counterpart of mailto.py.

Builds a wa.me link with a pre-filled text from an app_settings template and opens it in the
browser / WhatsApp app. Nothing is sent by BowTally: the user sends the message in WhatsApp.
No attachments (wa.me cannot carry files), no logging, no network access by BowTally itself.
"""
import re
import string
from urllib.parse import quote

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

from bowtally.services import markup
from bowtally.services import settings_service as ss
from bowtally.ui.components.toast import Toast
from bowtally.ui.utils.mailto import template_context, tournament_ctx

# tournament_ctx is shared with mailto.py (same placeholders), not duplicated here
__all__ = ["normalize_phone", "build_wa_url", "use_whatsapp_web", "render_template", "open_whatsapp",
           "send_whatsapp", "tournament_ctx"]

DEFAULT_COUNTRY_CODE = "49"
_E164 = re.compile(r"^\+[1-9]\d{7,14}$")      # country code + subscriber number, max 15 digits
_SEPARATORS = re.compile(r"[\s()\-/.]")


def normalize_phone(raw: str | None) -> str | None:
    """Normalize a phone number to E.164, e.g. '0171 1234567' -> '+491711234567'.

    Removes spaces, brackets, hyphens, slashes and dots; '00' becomes '+'; a leading '0' is
    replaced by '+49' unless the number already starts with '+'. '+49 (0) 171 …' drops the
    '(0)'. Returns None when the result is no plausible number (letters, too short or long,
    no '0' / '+' prefix)."""
    if not raw:
        return None
    s = raw.strip()
    s = re.sub(r"^(\+\d{1,3})\s*\(0\)", r"\1", s)          # +49 (0) 171 ... -> +49 171 ...
    s = _SEPARATORS.sub("", s)
    if s.startswith("00"):
        s = "+" + s[2:]
    elif s.startswith("0"):
        s = "+" + DEFAULT_COUNTRY_CODE + s[1:]
    return s if _E164.match(s) else None


def build_wa_url(phone_e164: str, text: str, web: bool = False) -> str:
    """https://wa.me/<number without '+'>?text=<url-encoded text>

    wa.me lets the browser hand over to the WhatsApp app (whatsapp:// link); without a working
    app association Windows reports "no app". web=True opens WhatsApp Web directly instead."""
    number, encoded = phone_e164.lstrip("+"), quote(text, safe="")
    if web:
        return f"https://web.whatsapp.com/send?phone={number}&text={encoded}"
    return f"https://wa.me/{number}?text={encoded}"


def use_whatsapp_web() -> bool:
    """Setting "WhatsApp öffnen mit": WhatsApp Web in the browser instead of the app."""
    return ss.get(ss.KEY_WHATSAPP_TARGET, "app") == "web"


def template_fields(template: str) -> set[str]:
    """Placeholder names used in a template ('{name}' -> 'name')."""
    names = set()
    for _literal, field, _spec, _conv in string.Formatter().parse(template):
        if field:
            names.add(re.split(r"[.\[]", field, maxsplit=1)[0])
    return names


def render_template(template_key: str, context: dict) -> tuple[str, list[str]]:
    """Text of the WhatsApp template with placeholders filled in, plus the placeholders that
    could not be resolved (they stay in the text as '{name}').
    Raises ValueError when the template is empty or malformed."""
    body_raw = ss.get(template_key) or ""
    if not body_raw.strip():
        raise ValueError("empty")
    ctx = template_context(context, with_logo=False)
    try:
        text = markup.to_whatsapp(body_raw).format_map(ctx)   # markup applies to the template only
    except (ValueError, AttributeError, IndexError, TypeError, KeyError) as exc:
        raise ValueError(f"malformed: {exc}") from exc
    unresolved = sorted(f for f in template_fields(body_raw) if f not in ctx)
    return text, unresolved


def _person(context: dict) -> str:
    return context.get("name") or " ".join(
        filter(None, [context.get("first_name"), context.get("last_name")])) or "Empfänger"


def open_whatsapp(template_key: str, raw_phone: str | None, context: dict,
                  parent=None) -> bool:
    """Counterpart of open_mailto(): open a WhatsApp chat with a pre-filled text.

    `template_key` is the full settings key of the body (whatsapp_<name>_body); there is no
    subject and no attachment. Shows a warning toast and returns False when the number is
    missing or invalid, the template is empty or malformed, or the link cannot be opened.
    Unknown placeholders are left in the text and reported. True: the chat was opened
    (that is not "sent" - the user sends the message in WhatsApp)."""
    name = _person(context)
    if not raw_phone or not raw_phone.strip():
        Toast.show(parent, f"Keine Telefonnummer für {name} hinterlegt", Toast.WARNING)
        return False
    phone = normalize_phone(raw_phone)
    if phone is None:
        Toast.show(parent, f"Telefonnummer von {name} ist ungültig: „{raw_phone}“. Bitte mit "
                           "Vorwahl angeben, z. B. 0171 1234567 oder +49 171 1234567.",
                   Toast.WARNING)
        return False
    try:
        text, unresolved = render_template(template_key, context)
    except ValueError as exc:
        reason = ("nicht konfiguriert (kein Text)" if str(exc) == "empty"
                  else "fehlerhaft (geschweifte Klammern prüfen)")
        Toast.show(parent, f"WhatsApp-Vorlage „{template_key}“ ist {reason}. Bitte unter "
                           "Einstellungen > WhatsApp-Vorlagen prüfen.", Toast.WARNING)
        return False
    web = use_whatsapp_web()
    if not QDesktopServices.openUrl(QUrl(build_wa_url(phone, text, web))):
        Toast.show(parent, "WhatsApp konnte nicht geöffnet werden. Ist ein Browser installiert?"
                   + ("" if web else " Alternativ unter Einstellungen > WhatsApp-Vorlagen "
                      "„WhatsApp Web im Browser“ wählen."), Toast.WARNING)
        return False
    if unresolved:
        Toast.show(parent, "Platzhalter ohne Wert in der WhatsApp-Vorlage: "
                   + ", ".join("{" + f + "}" for f in unresolved)
                   + " – bitte den Text vor dem Senden prüfen.", Toast.WARNING)
    return True


def send_whatsapp(parent, template_key: str, recipients: list[tuple[str, str | None, dict]],
                  title: str = "Nachricht per WhatsApp senden") -> None:
    """One recipient: open the chat directly. Several: the sequential WhatsAppSendDialog
    (each new wa.me call would replace the chat opened before). recipients: (name, phone, ctx)."""
    if not recipients:
        Toast.show(parent, "Keine Empfänger ausgewählt.", Toast.WARNING)
        return
    if len(recipients) == 1:
        _name, phone, ctx = recipients[0]
        open_whatsapp(template_key, phone, ctx, parent)
        return
    if not any(normalize_phone(phone) for _n, phone, _c in recipients):
        Toast.show(parent, "Keiner der ausgewählten Empfänger hat eine gültige Telefonnummer.",
                   Toast.WARNING)
        return
    from bowtally.ui.dialogs.whatsapp_send_dialog import WhatsAppSendDialog
    WhatsAppSendDialog(template_key, recipients, title, parent).exec()
