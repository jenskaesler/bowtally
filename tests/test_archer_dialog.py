# -*- coding: utf-8 -*-
import pytest

pytest.importorskip("PySide6")

from bowtally import config
from bowtally.database import engine
from bowtally.services import master_data_service as md


@pytest.fixture(autouse=True)
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "APP_DATA_DIR", tmp_path / "appdata")
    engine.init_database(f"sqlite:///{(tmp_path / 'd.db').as_posix()}")


@pytest.fixture
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _dialog(record=None):
    from bowtally.ui.views.archers_view import ArcherDialog
    return ArcherDialog(record)


def _tab_names(dialog):
    from PySide6.QtWidgets import QTabWidget
    tabs = dialog.findChild(QTabWidget)
    return [tabs.tabText(i) for i in range(tabs.count())]


def test_tabs_for_new_and_existing_archer(app):
    assert _tab_names(_dialog()) == ["Stammdaten", "Notizen", "Dokumente"]
    archer = md.save_archer({"first_name": "Anna", "last_name": "Alt"})
    assert _tab_names(_dialog(archer)) == ["Stammdaten", "Turnierhistorie", "Notizen", "Dokumente"]


def test_notes_have_their_own_tab_and_are_saved(app):
    dialog = _dialog()
    assert "notes" not in dialog.form.fields and "notes" in dialog.notes_form.fields
    dialog.form.fields["first_name"].set_value("Bernd")
    dialog.form.fields["last_name"].set_value("Bau")
    dialog.notes_form.fields["notes"].set_value("Wichtig")
    assert dialog._is_dirty() and dialog._do_save()
    assert [x.notes for x in md.list_archers() if x.id == dialog.saved_id] == ["Wichtig"]


def test_notes_field_takes_half_of_the_tab_height(app):
    from PySide6.QtWidgets import QTabWidget
    dialog = _dialog()
    dialog.show()
    tabs = dialog.findChild(QTabWidget)
    tabs.setCurrentIndex(_tab_names(dialog).index("Notizen"))
    app.processEvents()
    ratio = dialog.notes_form.fields["notes"].widget.height() / tabs.currentWidget().height()
    assert 0.45 < ratio < 0.55
    dialog.close()


def test_save_button_turns_red_on_change_in_any_tab(app):
    archer = md.save_archer({"first_name": "Anna", "last_name": "Alt"})
    dialog = _dialog(archer)
    dialog.show()
    assert not dialog._save_btn.property("dirty")
    dialog.notes_form.fields["notes"].set_value("Neu")
    assert dialog._save_btn.property("dirty") is True
    dialog.notes_form.fields["notes"].set_value("")
    assert dialog._save_btn.property("dirty") is False
    dialog.close()


def test_files_of_an_archer_can_be_added(app, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QFileDialog
    archer = md.save_archer({"first_name": "Anna", "last_name": "Alt"})
    source = tmp_path / "Antrag.pdf"
    source.write_bytes(b"pdf")
    monkeypatch.setattr(QFileDialog, "getOpenFileNames", staticmethod(lambda *a, **k: ([str(source)], "")))
    from bowtally.ui.components.files_panel import FilesPanel
    dialog = _dialog(archer)
    panel = dialog.findChild(FilesPanel)
    panel.add_files()
    assert panel.table.item(0, 0).text() == "Antrag.pdf"
    assert md.archer_file_path(md.list_archer_files(archer.id)[0]).read_bytes() == b"pdf"
    new_dialog = _dialog()
    assert new_dialog.findChild(FilesPanel).table is None
