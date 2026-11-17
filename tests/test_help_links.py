# -*- coding: utf-8 -*-
import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QFormLayout, QLabel


@pytest.fixture
def app(tmp_path):
    """QApplication with an ini-file QSettings, so the real registry values stay untouched."""
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path))
    yield QApplication.instance() or QApplication([])
    QSettings.setDefaultFormat(QSettings.Format.NativeFormat)


@pytest.fixture
def db(tmp_path, monkeypatch):
    from bowtally import config
    from bowtally.database.engine import init_database
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "bowtally.db")
    init_database()


def _links(widget):
    return [lbl for lbl in widget.findChildren(QLabel) if "href" in lbl.text()]


def test_help_link_opens_the_help_at_the_given_section(app, db, monkeypatch):
    from bowtally.ui.components.help_link import help_link
    from bowtally.ui.dialogs import help_dialog
    calls = []
    monkeypatch.setattr(help_dialog.HelpDialog, "show_section",
                        lambda self, title, anchor="": calls.append((title, anchor)))
    monkeypatch.setattr(help_dialog.HelpDialog, "exec", lambda self: 0)
    help_link("Backup & Updates", "backup-passwort", "Hilfe").linkActivated.emit("#")
    assert calls == [("Backup & Updates", "backup-passwort")]


@pytest.mark.parametrize("title, anchor", [("Ergebnisse & Wertung", "gleichstand"),
                                           ("Backup & Updates", "backup-passwort")])
def test_help_scrolls_to_the_anchor(app, db, title, anchor):
    from bowtally.ui.dialogs.help_dialog import HelpDialog
    dialog = HelpDialog()
    dialog.resize(700, 260)
    dialog.show()
    dialog.show_section(title, anchor)
    for _ in range(3):
        app.processEvents()
    assert dialog._browser.verticalScrollBar().value() > 0


def test_rule_dialog_points_to_the_help_in_the_checkbox_column(app, db):
    from bowtally.ui.views.rules_view import ScoringRuleDialog
    dialog = ScoringRuleDialog()
    assert not any("Kills zählen nur bei" in lbl.text() for lbl in dialog.findChildren(QLabel))
    (link,) = _links(dialog)
    assert dialog.form._lay.getWidgetPosition(link)[1] == QFormLayout.ItemRole.FieldRole


def test_every_help_link_of_the_settings_points_to_an_existing_anchor(app, db, monkeypatch):
    from bowtally.ui.dialogs import help_dialog, settings_dialog
    calls = []
    original = settings_dialog.help_link
    monkeypatch.setattr(settings_dialog, "help_link",
                        lambda *a, **k: calls.append(a[:2]) or original(*a, **k))
    dialog = settings_dialog.SettingsDialog(lambda *_: None)
    sections = dict(help_dialog._SECTIONS)
    assert {a for _s, a in calls} >= {"bankdaten", "textvorlagen", "platzhalter-email",
                                      "inventarkategorien", "erweitert", "backup-passwort"}
    for title, anchor in calls:
        assert f'<a name="{anchor}">' in sections[title], (title, anchor)
    texts = [lbl.text() for lbl in dialog.findChildren(QLabel)]
    assert not any("Platzhalter:" in t or "Platzhalter Verwendungszweck" in t for t in texts)


def test_settings_dialog_is_larger_and_points_to_the_help_for_the_backup_password(app, db):
    from bowtally.ui.dialogs.settings_dialog import SettingsDialog
    dialog = SettingsDialog(lambda *_: None)
    available = QApplication.primaryScreen().availableGeometry()
    assert dialog.width() >= min(1040, int(available.width() * 0.9))
    assert dialog.height() >= min(780, int(available.height() * 0.9))
    assert not any("Backups sind mit diesem Passwort" in lbl.text() for lbl in dialog.findChildren(QLabel))
    assert any("Backup-Passwort" in lbl.text() for lbl in _links(dialog))
