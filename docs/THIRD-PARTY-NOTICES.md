# Third-Party Notices

BowTally verwendet folgende Open-Source-Bibliotheken. Die jeweiligen Lizenztexte sind über
die angegebenen Quellen abrufbar.

## Laufzeit-Abhängigkeiten

### PySide6

- **Lizenz:** GNU Lesser General Public License v3 (LGPL-3.0)
- **Urheber:** The Qt Company Ltd.
- **Quelle:** https://www.qt.io/qt-for-python
- **Lizenztext:** https://www.gnu.org/licenses/lgpl-3.0.html

PySide6 wird als dynamisch gebundene Bibliothek eingebunden. Nutzer können PySide6
unabhängig von BowTally aktualisieren oder ersetzen. Der Quellcode von PySide6 ist
unter https://code.qt.io/cgit/pyside/pyside-setup.git/ verfügbar.

### SQLAlchemy

- **Lizenz:** MIT License
- **Urheber:** Mike Bayer und Mitwirkende
- **Quelle:** https://www.sqlalchemy.org/
- **Lizenztext:** https://github.com/sqlalchemy/sqlalchemy/blob/main/LICENSE

### Alembic

- **Lizenz:** MIT License
- **Urheber:** Mike Bayer und Mitwirkende
- **Quelle:** https://alembic.sqlalchemy.org/
- **Lizenztext:** https://github.com/sqlalchemy/alembic/blob/main/LICENSE

### reportlab

- **Lizenz:** BSD License
- **Urheber:** ReportLab Inc. und Mitwirkende
- **Quelle:** https://www.reportlab.com/opensource/
- **Lizenztext:** https://hg.reportlab.com/hg-public/reportlab/file/tip/LICENSE.txt

### openpyxl

- **Lizenz:** MIT License
- **Urheber:** Eric Gazoni, Charlie Clark und Mitwirkende
- **Quelle:** https://openpyxl.readthedocs.io/
- **Lizenztext:** https://foss.heptapod.net/openpyxl/openpyxl/-/blob/branch/3.1/LICENCE.rst

## Build- und Entwicklungs-Abhängigkeiten

Die folgenden Werkzeuge werden ausschließlich für Build und Entwicklung verwendet und
sind nicht Bestandteil der verteilten Anwendung.

| Paket | Lizenz | Quelle |
|---|---|---|
| PyInstaller | GPL-2.0 (mit Ausnahme für gepackte Anwendungen) | https://pyinstaller.org/ |
| pytest | MIT | https://pytest.org/ |
| NSIS | zlib/libpng License | https://nsis.sourceforge.io/ |

## Hinweis zur LGPL-Konformität (PySide6)

BowTally verteilt PySide6 nicht statisch gebunden. Der Installer legt PySide6 als
eigenständiges Python-Paket ab, das unabhängig aktualisiert oder ausgetauscht werden kann.
Der Quellcode von PySide6 ist öffentlich zugänglich (siehe oben). Eine Kopie der
LGPL v3 liegt unter https://www.gnu.org/licenses/lgpl-3.0.html.
