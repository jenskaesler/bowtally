# -*- coding: utf-8 -*-
import json
import sqlite3

import pytest

pytest.importorskip("PySide6")

from bowtally import config
from bowtally.database import engine
from bowtally.services import settings_service as ss

FAMILIES = list(config.BUNDLED_FONTS)


@pytest.fixture(autouse=True)
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "APP_DATA_DIR", tmp_path / "appdata")
    engine.init_database(f"sqlite:///{(tmp_path / 'd.db').as_posix()}")


@pytest.fixture
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_three_families_with_regular_bold_and_license_are_shipped():
    assert FAMILIES == ["Open Sans", "Inter", "Source Sans 3"]
    for regular, bold in config.BUNDLED_FONTS.values():
        for name in (regular, bold):
            assert (config.FONTS_DIR / name).stat().st_size > 50_000
    assert sorted(p.name for p in (config.FONTS_DIR / "licenses").glob("OFL-*.txt")) == \
        ["OFL-Inter.txt", "OFL-OpenSans.txt", "OFL-SourceSans3.txt"]


@pytest.mark.parametrize("family", FAMILIES)
def test_pdf_uses_the_bundled_font_even_if_not_installed(family, tmp_path):
    from reportlab.pdfgen import canvas
    from bowtally.reports import templates as tpl
    regular, bold = tpl.register_fonts([family])
    assert (regular, bold) == (family.replace(" ", ""), family.replace(" ", "") + "-Bold")
    pdf = canvas.Canvas(str(tmp_path / "t.pdf"))
    pdf.setFont(regular, 12)
    pdf.drawString(50, 750, "Größe Ärger 123")
    pdf.setFont(bold, 12)
    pdf.drawString(50, 730, "Fett")
    pdf.save()
    assert (tmp_path / "t.pdf").read_bytes().startswith(b"%PDF")


def test_unknown_family_falls_back_to_helvetica():
    from bowtally.reports import templates as tpl
    assert tpl.register_fonts(["Gibt es nicht"]) == (tpl.FALLBACK_FONT, tpl.FALLBACK_FONT_BOLD)


def test_qt_knows_the_bundled_families(app):
    from PySide6.QtGui import QFontDatabase
    from bowtally.ui import theme
    theme.load_bundled_fonts()
    assert all(QFontDatabase.hasFamily(family) for family in FAMILIES)


def _dialog(app):
    from bowtally.ui.dialogs.settings_dialog import SettingsDialog
    return SettingsDialog(lambda *_: None)


def test_font_is_a_combo_with_the_bundled_fonts(app):
    combo = _dialog(app).value_widgets[ss.KEY_FONT_FAMILY]
    assert [combo.itemData(i) for i in range(combo.count())] == [*FAMILIES, "Segoe UI"]
    assert combo.currentData() == "Open Sans"


def test_free_text_font_from_an_older_version_is_kept(app):
    ss.set_value(ss.KEY_FONT_FAMILY, "Calibri")
    dialog = _dialog(app)
    combo = dialog.value_widgets[ss.KEY_FONT_FAMILY]
    assert combo.currentData() == "Calibri" and combo.count() == len(FAMILIES) + 2
    dialog._save_settings()
    assert ss.get(ss.KEY_FONT_FAMILY) == "Calibri"


def _backup_and_restore(tmp_path, monkeypatch, family, drop_font=False):
    from bowtally.services import backup_service
    ss.set_value(ss.KEY_FONT_FAMILY, family)
    with engine.session_scope() as s:
        backup = json.loads(json.dumps(backup_service.create_backup(s, "test")))
    if drop_font:
        backup["data"]["app_settings"] = [r for r in backup["data"]["app_settings"]
                                          if r["key"] != ss.KEY_FONT_FAMILY]
    db_path = tmp_path / "restored.db"
    monkeypatch.setattr(config, "DB_PATH", db_path)
    backup_service._restore_impl(backup)
    with sqlite3.connect(db_path) as con:
        return con.execute("SELECT value FROM app_settings WHERE key='font_family'").fetchone()


@pytest.mark.parametrize("family", ["Inter", "Calibri"])
def test_font_choice_survives_backup_and_restore(tmp_path, monkeypatch, family):
    assert _backup_and_restore(tmp_path, monkeypatch, family) == (family,)


def test_old_backup_without_font_keeps_the_default(tmp_path, monkeypatch):
    assert _backup_and_restore(tmp_path, monkeypatch, "Inter", drop_font=True) == ("Open Sans",)
