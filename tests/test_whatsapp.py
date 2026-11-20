# -*- coding: utf-8 -*-
"""WhatsApp click-to-chat (wa.me): number normalization, link, template handling, sequential
sending to several recipients."""
from urllib.parse import parse_qs, urlparse

import pytest

pytest.importorskip("PySide6")

from bowtally import config
from bowtally.database import engine
from bowtally.services import settings_service as ss
from bowtally.ui.utils import whatsapp as wa


@pytest.mark.parametrize("raw, expected", [
    ("0171 1234567", "+491711234567"),               # German number with leading 0
    ("(0171) 123-45/67", "+491711234567"),           # brackets, hyphen, slash
    ("+49 171 1234567", "+491711234567"),            # already international
    ("+49 (0) 171 1234567", "+491711234567"),        # the (0) of German notation
    ("0049 171 1234567", "+491711234567"),           # 00 instead of +
    ("+43 664 1234567", "+436641234567"),            # other country stays
    ("089.123456", "+4989123456"),
])
def test_normalize_phone(raw, expected):
    assert wa.normalize_phone(raw) == expected


@pytest.mark.parametrize("raw", [None, "", "   ", "0171 12345ab", "0123", "1711234567",
                                 "+49", "+0171234567", "+4917112345678901234"])
def test_normalize_phone_rejects_implausible_numbers(raw):
    assert wa.normalize_phone(raw) is None


def test_build_wa_url_encodes_the_text():
    url = wa.build_wa_url("+491711234567", "Hallo Anna & Co.\nZeile 2 – 100 %")
    parts = urlparse(url)
    assert (parts.scheme, parts.netloc, parts.path) == ("https", "wa.me", "/491711234567")
    assert parse_qs(parts.query)["text"] == ["Hallo Anna & Co.\nZeile 2 – 100 %"]
    assert "&Co" not in url and " " not in url


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "APP_DATA_DIR", tmp_path / "appdata")
    engine.init_database(f"sqlite:///{(tmp_path / 'd.db').as_posix()}")


@pytest.fixture
def opened(monkeypatch):
    """Records the opened URLs instead of opening a browser; collects the toasts."""
    calls = {"urls": [], "toasts": [], "result": True}
    monkeypatch.setattr(wa.QDesktopServices, "openUrl",
                        lambda url: calls["urls"].append(url.toString()) or calls["result"])
    monkeypatch.setattr(wa.Toast, "show",
                        lambda parent, text, kind=None, action=None: calls["toasts"].append(text))
    return calls


def _text(url: str) -> str:
    return parse_qs(urlparse(url).query)["text"][0]


def test_seeded_templates_exist_for_all_six_touchpoints(db):
    for key in (ss.KEY_WHATSAPP_TPL_CONFIRMATION, ss.KEY_WHATSAPP_TPL_PAYMENT,
                ss.KEY_WHATSAPP_TPL_DOCS, ss.KEY_WHATSAPP_TPL_WAITLIST,
                ss.KEY_WHATSAPP_TPL_HELPER, ss.KEY_WHATSAPP_TPL_DATA_REQUEST):
        assert ss.get(key), key


def test_open_whatsapp_fills_the_template(db, opened):
    ss.set_value(ss.KEY_WHATSAPP_TPL_CONFIRMATION, "Hallo {first_name}, {turniername} am {datum}.")
    assert wa.open_whatsapp(ss.KEY_WHATSAPP_TPL_CONFIRMATION, "0171 1234567",
                            {"first_name": "Anna", "turniername": "Waldturnier",
                             "datum": "01.06.2027"})
    (url,) = opened["urls"]
    assert url.startswith("https://wa.me/491711234567?text=")
    assert _text(url) == "Hallo Anna, Waldturnier am 01.06.2027."
    assert opened["toasts"] == []


@pytest.mark.parametrize("phone, message", [
    (None, "Keine Telefonnummer für Anna Alt"),
    ("0171 abc", "Telefonnummer von Anna Alt ist ungültig"),
])
def test_missing_or_invalid_number_warns_and_opens_nothing(db, opened, phone, message):
    assert not wa.open_whatsapp(ss.KEY_WHATSAPP_TPL_CONFIRMATION, phone, {"name": "Anna Alt"})
    assert opened["urls"] == [] and message in opened["toasts"][0]


def test_empty_template_warns(db, opened):
    ss.set_value(ss.KEY_WHATSAPP_TPL_PAYMENT, "   ")
    assert not wa.open_whatsapp(ss.KEY_WHATSAPP_TPL_PAYMENT, "0171 1234567", {"name": "A"})
    assert opened["urls"] == [] and "nicht konfiguriert" in opened["toasts"][0]


def test_malformed_template_warns(db, opened):
    ss.set_value(ss.KEY_WHATSAPP_TPL_PAYMENT, "Hallo {first_name")
    assert not wa.open_whatsapp(ss.KEY_WHATSAPP_TPL_PAYMENT, "0171 1234567", {"name": "A"})
    assert opened["urls"] == [] and "fehlerhaft" in opened["toasts"][0]


def test_unknown_placeholder_stays_in_the_text_and_is_reported(db, opened):
    ss.set_value(ss.KEY_WHATSAPP_TPL_DOCS, "Hallo {first_name}, Tisch {tischnummer}")
    assert wa.open_whatsapp(ss.KEY_WHATSAPP_TPL_DOCS, "0171 1234567", {"first_name": "Anna"})
    assert _text(opened["urls"][0]) == "Hallo Anna, Tisch {tischnummer}"
    assert "{tischnummer}" in opened["toasts"][0]


def test_link_that_cannot_be_opened_warns(db, opened):
    opened["result"] = False
    assert not wa.open_whatsapp(ss.KEY_WHATSAPP_TPL_CONFIRMATION, "0171 1234567",
                                {"name": "Anna"})
    assert "konnte nicht geöffnet werden" in opened["toasts"][0]


def test_send_whatsapp_without_recipients_warns(db, opened):
    wa.send_whatsapp(None, ss.KEY_WHATSAPP_TPL_WAITLIST, [])
    assert opened["toasts"] == ["Keine Empfänger ausgewählt."] and opened["urls"] == []


def test_sequential_dialog_is_controlled_by_the_user(db, opened):
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from bowtally.ui.dialogs import whatsapp_send_dialog as wsd
    ss.set_value(ss.KEY_WHATSAPP_TPL_WAITLIST, "Hallo {first_name}")
    recipients = [("Alt, Anna", "0171 1111111", {"first_name": "Anna"}),
                  ("Bach, Bert", None, {"first_name": "Bert"}),             # no number
                  ("Cord, Carl", "+49 171 3333333", {"first_name": "Carl"}),
                  ("Dorn, Dora", "0171 4444444", {"first_name": "Dora"})]
    dlg = wsd.WhatsAppSendDialog(ss.KEY_WHATSAPP_TPL_WAITLIST, recipients)
    assert dlg.status == [wsd.OPEN, wsd.NO_PHONE, wsd.OPEN, wsd.OPEN]
    assert dlg.current() == 0 and opened["urls"] == []      # nothing opens by itself

    dlg.open_current()
    assert dlg.status[0] == wsd.OPENED and len(opened["urls"]) == 1
    assert _text(opened["urls"][0]) == "Hallo Anna"
    dlg.mark_sent()                                          # only the user confirms
    assert dlg.status[0] == wsd.CONFIRMED
    assert dlg.current() == 0                                # no automatic next step

    dlg.next_recipient()                                     # skips the one without number
    assert dlg.current() == 2
    dlg.next_recipient()                                     # moved on without opening
    assert dlg.status[2] == wsd.SKIPPED and dlg.current() == 3
    dlg.open_current()
    assert dlg.status[3] == wsd.OPENED                       # opened, but not "sent"
    assert len(opened["urls"]) == 2
    assert dlg.progress.text().startswith("4 von 4 bearbeitet")
    assert "1 als gesendet markiert" in dlg.progress.text()
