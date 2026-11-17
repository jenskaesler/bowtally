# -*- coding: utf-8 -*-
from bowtally import config


def test_development_reads_the_license_in_the_repo_root():
    assert config.license_text().startswith("BowTally Non-Commercial-Distribution Copyleft License")


def test_installed_copy_next_to_the_exe_wins(tmp_path, monkeypatch):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "LICENSE.txt").write_text("Installierte Lizenz", encoding="utf-8")
    monkeypatch.setattr(config, "INSTALL_DIR", tmp_path)
    assert config.license_text() == "Installierte Lizenz"
    (tmp_path / "LICENSE.txt").write_text("Lizenz im Installationsordner", encoding="utf-8")
    assert config.license_text() == "Lizenz im Installationsordner"


def test_missing_installed_copy_falls_back_to_the_bundled_license(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "INSTALL_DIR", tmp_path)
    assert config.license_text().startswith("BowTally Non-Commercial-Distribution")
