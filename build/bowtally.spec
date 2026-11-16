# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for BowTally (onedir, windowed).
# Run from the repository root:  python -m PyInstaller build\bowtally.spec --noconfirm
import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
PKG = os.path.join(ROOT, "bowtally")

datas = [
    # Alembic migrations are loaded from disk at runtime -> ship them as files
    (os.path.join(PKG, "database", "migrations"), "bowtally/database/migrations"),
    (os.path.join(PKG, "database", "alembic.ini"), "bowtally/database"),
    (os.path.join(ROOT, "assets"), "assets"),
    (os.path.join(ROOT, "docs", "license.txt"), "docs"),
]
datas += collect_data_files("reportlab")
# Qt plugins (platforms, styles, imageformats, ...) are collected by the PySide6 hooks
# shipped with PyInstaller; listing them here again would duplicate them.

hiddenimports = (collect_submodules("alembic") + collect_submodules("bowtally")
                 + ["sqlalchemy.dialects.sqlite", "odf.opendocument", "odf.table",
                    "odf.text", "odf.teletype"])

# Large Qt modules BowTally never uses
excludes = ["PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngine",
            "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.QtMultimedia",
            "PySide6.QtQuick", "PySide6.QtQml", "PySide6.QtPdf", "PySide6.QtPdfWidgets",
            "PySide6.QtCharts", "PySide6.QtDataVisualization", "tkinter", "pytest"]

a = Analysis(
    [os.path.join(PKG, "main.py")],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,      # onefile = False -> onedir
    name="BowTally",
    debug=False,
    strip=False,
    upx=False,
    console=False,              # windowed
    icon=os.path.join(ROOT, "assets", "icon.ico"),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="BowTally",
)
