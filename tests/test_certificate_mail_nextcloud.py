# -*- coding: utf-8 -*-
import datetime
import types
from email import message_from_bytes, policy

import pytest

pytest.importorskip("PySide6")

from bowtally import config
from bowtally.database import engine

PROPFIND = b"""<?xml version="1.0"?>
<d:multistatus xmlns:d="DAV:">
 <d:response><d:href>/remote.php/dav/files/u/B/</d:href></d:response>
 <d:response><d:href>/remote.php/dav/files/u/B/bowtally_backup_2026-01-01-000000.zip</d:href>
  <d:propstat><d:prop><d:getlastmodified>Thu, 01 Jan 2026 10:00:00 GMT</d:getlastmodified>
  </d:prop></d:propstat></d:response>
 <d:response><d:href>/remote.php/dav/files/u/B/bowtally_backup_2026-01-02-000000.zip</d:href>
  <d:propstat><d:prop><d:getlastmodified>Fri, 02 Jan 2026 10:00:00 GMT</d:getlastmodified>
  </d:prop></d:propstat></d:response>
 <d:response><d:href>/remote.php/dav/files/u/B/notes.txt</d:href></d:response>
</d:multistatus>"""


def test_nextcloud_prune_deletes_only_old_backups(monkeypatch):
    import urllib.request
    from bowtally.services import backup_service as bs
    calls = []

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return PROPFIND

    def fake_open(req, timeout=None):
        calls.append((req.get_method(), req.full_url))
        return Resp()

    monkeypatch.setattr(urllib.request, "urlopen", fake_open)
    bs._nc_prune("https://nc.example/remote.php/dav/files/u/B/", "Basic x", 1)
    assert calls[1:] == [("DELETE", "https://nc.example/remote.php/dav/files/u/B/"
                                    "bowtally_backup_2026-01-01-000000.zip")]


@pytest.fixture
def tournament(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "APP_DATA_DIR", tmp_path / "appdata")
    engine.init_database(f"sqlite:///{(tmp_path / 'd.db').as_posix()}")
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from bowtally.services import master_data_service as md, settings_service as ss
    from bowtally.services import tournament_service as ts
    return ts.save_tournament({"name": "T", "date": datetime.date.today(), "num_targets": 1,
                               "scoring_rule_id": int(ss.get("default_scoring_rule_id"))},
                              [bc.id for bc in md.list_bow_classes()])


def test_certificate_has_logo_both_boards_and_filters_participant(tournament, monkeypatch,
                                                                  tmp_path):
    from PySide6.QtGui import QColor, QImage
    from bowtally.reports import certificates as cert
    from bowtally.services import master_data_service as md, settings_service as ss
    logo = tmp_path / "logo.png"
    img = QImage(40, 40, QImage.Format.Format_RGB32)
    img.fill(QColor("red"))
    img.save(str(logo))
    ss.save_club_profile({"logo_path": str(logo), "first_board_fname": "Anna",
                          "first_board_lname": "Eins", "second_board_fname": "Bert",
                          "second_board_lname": "Zwei"})
    bc = md.list_bow_classes()[0]
    entry = lambda r: types.SimpleNamespace(rank=r, name=f"P{r}", total=100 - r,
                                            participant_id=r)
    monkeypatch.setattr(cert.rs, "compute_ranking",
                        lambda tid, **k: {bc.id: [entry(1), entry(2), entry(3), entry(4)]})
    signed = []
    real = cert._signature
    monkeypatch.setattr(cert, "_signature",
                        lambda c, cx, base, name, role, font: (signed.append((name, role)),
                                                               real(c, cx, base, name, role, font)))
    data = cert.build_certificates(tournament.id, tmp_path / "u.pdf").read_bytes()
    assert b"/Subtype /Image" in data
    assert signed[:2] == [("Anna Eins", "1. Vorsitzende/r"), ("Bert Zwei", "2. Vorsitzende/r")]
    one = cert.build_certificates(tournament.id, tmp_path / "one.pdf", participant_id=2)
    assert one.read_bytes().count(b"/Type /Page\n") + one.read_bytes().count(b"/Type /Page ") == 1
    assert cert.podium_participant_ids(tournament.id) == {1, 2, 3}


def test_mail_carries_several_attachments(tournament, monkeypatch, tmp_path):
    from bowtally.ui.utils import mailto
    opened = []
    monkeypatch.setattr(mailto.exporter, "open_file", opened.append)
    a, b = tmp_path / "Ergebnisse.pdf", tmp_path / "Urkunde.pdf"
    a.write_bytes(b"%PDF-a")
    b.write_bytes(b"%PDF-b")
    mailto.open_mailto("email_results", "x@example.org", {"name": "X"}, attachment=[a, b])
    msg = message_from_bytes(open(opened[0], "rb").read(), policy=policy.default)
    assert [p.get_filename() for p in msg.iter_attachments()] == ["Ergebnisse.pdf",
                                                                  "Urkunde.pdf"]


def test_every_pdf_builder_uses_the_watermark_canvas():
    from pathlib import Path
    import bowtally.reports as reports
    for f in Path(reports.__file__).parent.glob("*.py"):
        src = f.read_text(encoding="utf-8")
        assert src.count("doc.build(") == src.count("canvasmaker=tpl.WatermarkCanvas"), f.name
        assert "canvas.Canvas(" not in src, f.name


def test_watermark_links_to_repository(tmp_path):
    from bowtally.reports import templates as tpl
    c = tpl.WatermarkCanvas(str(tmp_path / "w.pdf"))
    c.drawString(100, 700, "x")
    c.showPage()
    c.save()
    data = (tmp_path / "w.pdf").read_bytes()
    assert tpl.REPO_URL.encode() in data and b"/Subtype /Image" in data


def test_status_bar_shows_schema_version(tournament):
    from bowtally.ui.widgets.status_bar import StatusBar
    from PySide6.QtWidgets import QLabel
    rev = engine.schema_version()
    assert rev and rev[:4].isdigit()
    bar = StatusBar()
    texts = [w.text() for w in bar.findChildren(QLabel)]
    assert any(f"Schema {rev.split('_', 1)[0]}" in t for t in texts)


def test_about_and_splash_show_schema(tournament):
    from bowtally.main import _Splash
    from bowtally.ui.dialogs.about_dialog import AboutDialog
    number = engine.schema_number()
    dlg = AboutDialog()
    assert any(f"Datenbankschema {number}" in b.toPlainText()
               for b in dlg.findChildren(__import__("PySide6.QtWidgets").QtWidgets.QTextBrowser))
    splash = _Splash()
    splash.show_schema(number)
    assert not splash.pixmap().isNull()
    splash.close()


def test_backup_info_file_has_schema_version(tournament, tmp_path):
    pyzipper = pytest.importorskip("pyzipper")
    from bowtally import __version__
    from bowtally.services import backup_service as bs
    with engine.session_scope() as s:
        backup = bs.create_backup(s, __version__)
    bs.save_backup_to_zip(backup, tmp_path / "b.zip", None, "pw")
    with pyzipper.AESZipFile(tmp_path / "b.zip") as zf:
        zf.setpassword(b"pw")
        info = zf.read("bowtally.info").decode("utf-8")
    assert f"schema_version: {engine.schema_version()}\n" in info
