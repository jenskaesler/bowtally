# -*- coding: utf-8 -*-
import pytest

pytest.importorskip("PySide6")

from bowtally.updater import download_dialog as dd


class _Info:
    version = "2099.1.0"
    asset_url = "https://example.invalid/setup.exe"
    checksum_available = True
    checksum = "x"


@pytest.fixture
def dialog(monkeypatch):
    from PySide6.QtWidgets import QApplication, QMessageBox
    QApplication.instance() or QApplication([])
    monkeypatch.setattr(dd.DownloadDialog, "_start", lambda self: None)     # no download
    monkeypatch.setattr(QMessageBox, "critical", lambda *a, **k: None)
    return dd.DownloadDialog(_Info())


def _install(dialog, monkeypatch, code):
    from PySide6.QtWidgets import QApplication
    calls, quits = [], []
    monkeypatch.setattr(dd, "_run_elevated", lambda path, params: calls.append((path, params)) or code)
    monkeypatch.setattr(QApplication.instance(), "quit", lambda: quits.append(True))
    dialog._install()
    return calls, quits


def test_installer_is_started_with_the_admin_prompt_and_the_app_quits(dialog, monkeypatch):
    calls, quits = _install(dialog, monkeypatch, 42)
    assert calls[0][0] == dialog.dest and calls[0][1].startswith("/S ") and quits == [True]


def test_declined_admin_prompt_keeps_the_app_running(dialog, monkeypatch):
    calls, quits = _install(dialog, monkeypatch, dd.ERROR_ACCESS_DENIED)
    assert len(calls) == 1 and quits == []


def test_other_error_codes_keep_the_app_running(dialog, monkeypatch):
    assert _install(dialog, monkeypatch, 2)[1] == []
