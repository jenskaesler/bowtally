# -*- coding: utf-8 -*-
import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QPushButton


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
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "bowtally.db")
    from bowtally.database.engine import init_database
    init_database()


def _needs_big_screen(app):
    if app.primaryScreen().availableGeometry().height() < 900:
        pytest.skip("screen too small: dialog height is capped at 90 % of the screen")


def test_member_dialog_shows_all_tabs_without_scrolling(app, db):
    _needs_big_screen(app)
    from bowtally.services import member_service as ms
    from bowtally.ui.views.members_view import MemberDialog
    member = ms.create_member({"member_number": "1", "first_name": "A", "last_name": "B"})
    dialog = MemberDialog(ms.get_member(member.id))
    dialog.show()
    app.processEvents()
    for tab in range(dialog._tabs.count()):
        dialog._tabs.setCurrentIndex(tab)
        app.processEvents()
        assert dialog._scroll.verticalScrollBar().maximum() == 0, dialog._tabs.tabText(tab)
    dialog.reject()


def test_copy_button_sits_behind_the_account_holder_field(app, db):
    from bowtally.ui.views.members_view import MemberDialog
    dialog = MemberDialog()
    dialog.show()
    dialog._tabs.setCurrentIndex(1)
    app.processEvents()
    holder = dialog.bank_form.fields["account_holder"]
    copy_button = holder.findChild(QPushButton)
    assert copy_button.x() >= holder.widget.x() + holder.widget.width()
    assert copy_button.geometry().intersects(holder.widget.geometry().adjusted(-999, 0, 999, 0))
    dialog.reject()


@pytest.mark.parametrize("target_index", [0, 1, 2])
def test_backup_target_page_is_never_squeezed_in_small_settings_dialog(app, db, target_index):
    from bowtally.ui.dialogs.settings_dialog import SettingsDialog
    dialog = SettingsDialog(lambda *_: None)
    dialog.resize(900, 640)
    dialog.show()
    dialog._select_settings_page("backup")
    dialog._backup_target_combo.setCurrentIndex(target_index)
    app.processEvents()
    stack, page = dialog._backup_stack, dialog._backup_stack.currentWidget()
    assert stack.height() >= page.sizeHint().height()
    for button in page.findChildren(QPushButton):
        assert button.mapTo(stack, button.rect().bottomLeft()).y() <= stack.height(), button.text()
    dialog.hide()
