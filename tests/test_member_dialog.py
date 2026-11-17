# -*- coding: utf-8 -*-
from datetime import date

import pytest

pytest.importorskip("PySide6")

from bowtally import config
from bowtally.database import engine
from bowtally.services import member_service as ms


@pytest.fixture(autouse=True)
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "APP_DATA_DIR", tmp_path / "appdata")
    engine.init_database(f"sqlite:///{(tmp_path / 'd.db').as_posix()}")


@pytest.fixture
def app(monkeypatch):
    from PySide6.QtWidgets import QApplication
    from bowtally.ui.views import members_view
    app = QApplication.instance() or QApplication([])
    app.errors = []     # a real error dialog is modal and would hang the test
    monkeypatch.setattr(members_view, "show_error", lambda _parent, exc, *_: app.errors.append(exc))
    return app


def _dialog(record=None):
    from bowtally.ui.views.members_view import MemberDialog
    return MemberDialog(record)


def _member(**extra):
    return ms.create_member({"member_number": "1", "first_name": "Anna", "last_name": "Alt", **extra})


def test_consent_date_is_shown_with_today_and_hidden_again(app):
    dialog = _dialog()
    field = dialog.form.fields["consent_date"]
    assert field.isHidden()
    dialog.form.fields["consent_given"].set_value(True)
    assert not field.isHidden() and field.value() == date.today()
    dialog.form.fields["consent_given"].set_value(False)
    assert field.isHidden() and field.value() is None


def test_existing_consent_date_is_kept_and_shown(app):
    dialog = _dialog(_member(consent_given=True, consent_date=date(2025, 1, 2)))
    field = dialog.form.fields["consent_date"]
    assert not field.isHidden() and field.value() == date(2025, 1, 2)


def test_consent_fields_sit_above_the_mail_info_and_helper_is_renamed(app):
    dialog = _dialog()
    fields = dialog.form
    order = list(fields.fields)
    assert order.index("consent_given") < order.index("consent_date") < order.index("info_by_mail")
    assert fields.fields["is_tournament_helper"].widget.text() == "Ist Helfer"


def test_helper_history_tab_follows_the_helper_checkbox(app):
    dialog = _dialog()
    tabs = dialog._tabs
    names = [tabs.tabText(i) for i in range(tabs.count())]
    assert names == ["Basisdaten", "Bankverbindung", "Helferhistorie", "Notizen"]
    history = names.index("Helferhistorie")
    assert not tabs.isTabVisible(history)
    dialog.form.fields["is_tournament_helper"].set_value(True)
    assert tabs.isTabVisible(history)
    dialog.form.fields["is_tournament_helper"].set_value(False)
    assert not tabs.isTabVisible(history)
    assert _dialog(_member(is_tournament_helper=True))._tabs.isTabVisible(history)


def test_notes_live_in_their_own_last_tab_and_are_saved(app):
    dialog = _dialog()
    assert "notes" not in dialog.form.fields and "notes" in dialog.notes_form.fields
    for key, value in (("member_number", "7"), ("first_name", "Bernd"), ("last_name", "Bau")):
        dialog.form.fields[key].set_value(value)
    dialog.notes_form.fields["notes"].set_value("Wichtig")
    assert dialog._is_dirty() and dialog._do_save()
    assert ms.get_member(dialog.saved_id).notes == "Wichtig"


def test_files_can_be_added_and_removed_for_a_saved_member(app, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QFileDialog
    from bowtally.ui.components.confirm_dialog import ConfirmDialog
    member = _member()
    source = tmp_path / "Antrag.pdf"
    source.write_bytes(b"pdf")
    monkeypatch.setattr(QFileDialog, "getOpenFileNames", staticmethod(lambda *a, **k: ([str(source)], "")))
    monkeypatch.setattr(ConfirmDialog, "ask", staticmethod(lambda *a, **k: True))
    dialog = _dialog(member)

    dialog._add_files()
    assert dialog._files_table.rowCount() == 1
    assert dialog._files_table.item(0, 0).text() == "Antrag.pdf"
    stored = ms.list_member_files(member.id)[0]
    assert ms.member_file_path(stored).read_bytes() == b"pdf"

    dialog._files_table.selectRow(0)
    dialog._remove_file()
    assert dialog._files_table.rowCount() == 0 and ms.list_member_files(member.id) == []
    assert app.errors == []


def test_new_member_gets_a_hint_instead_of_the_file_list(app):
    assert not hasattr(_dialog(), "_files_table")


def test_notes_have_the_label_above_and_use_the_full_width(app):
    from PySide6.QtWidgets import QFormLayout
    dialog = _dialog()
    assert dialog.notes_form._lay.rowWrapPolicy() == QFormLayout.RowWrapPolicy.WrapAllRows


def test_list_headers_in_the_dialog_are_left_aligned(app):
    from PySide6.QtCore import Qt
    dialog = _dialog(_member())
    for table in (dialog._files_table, dialog._history):
        assert table.horizontalHeader().defaultAlignment() & Qt.AlignmentFlag.AlignLeft
