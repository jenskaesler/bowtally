# -*- coding: utf-8 -*-
"""Write tables as CSV/XLSX/ODS."""
import csv
import os
import re
from datetime import date
from pathlib import Path

FILE_FILTER = "Excel (*.xlsx);;OpenDocument (*.ods);;CSV (*.csv)"

Sheet = tuple[str, list[str], list[list]]   # (name, headers, rows)


def _cell(value):
    if isinstance(value, date):
        return value.strftime("%d.%m.%Y")
    return "" if value is None else value


def _sheet_title(name: str) -> str:
    return re.sub(r"[\\/*?:\[\]]", "-", name)[:31] or "Tabelle"


def _write_csv(path: Path, sheets: list[Sheet]) -> list[Path]:
    """One file per sheet: first sheet at path, others as <stem>_<sheet>.csv."""
    written = []
    for i, (name, headers, rows) in enumerate(sheets):
        p = path if i == 0 else path.with_name(
            f"{path.stem}_{re.sub(r'[^A-Za-z0-9_-]+', '_', name)}{path.suffix}")
        with p.open("w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh, delimiter=";")
            w.writerow(headers)
            w.writerows([[_cell(v) for v in r] for r in rows])
        written.append(p)
    return written


def _write_xlsx(path: Path, sheets: list[Sheet]) -> list[Path]:
    from openpyxl import Workbook
    from openpyxl.styles import Font
    wb = Workbook()
    wb.remove(wb.active)
    for name, headers, rows in sheets:
        ws = wb.create_sheet(_sheet_title(name))
        ws.append(headers)
        for c in ws[1]:
            c.font = Font(bold=True)
        for r in rows:
            ws.append([_cell(v) for v in r])
        for col in ws.columns:
            width = max((len(str(c.value)) for c in col if c.value is not None), default=8)
            ws.column_dimensions[col[0].column_letter].width = min(width + 2, 50)
    wb.save(path)
    return [path]


def _write_ods(path: Path, sheets: list[Sheet]) -> list[Path]:
    from odf.opendocument import OpenDocumentSpreadsheet
    from odf.table import Table, TableCell, TableRow
    from odf.text import P
    doc = OpenDocumentSpreadsheet()
    for name, headers, rows in sheets:
        table = Table(name=_sheet_title(name))
        for r in [headers] + rows:
            tr = TableRow()
            for v in r:
                v = _cell(v)
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    cell = TableCell(valuetype="float", value=v)
                else:
                    cell = TableCell(valuetype="string")
                cell.addElement(P(text=str(v)))
                tr.addElement(cell)
            table.addElement(tr)
        doc.spreadsheet.addElement(table)
    doc.save(str(path))
    return [path]


def write_sheets(path: str | Path, sheets: list[Sheet]) -> list[Path]:
    path = Path(path)
    writer = {".csv": _write_csv, ".xlsx": _write_xlsx, ".ods": _write_ods}.get(
        path.suffix.lower())
    if writer is None:
        raise ValueError(f"Nicht unterstütztes Dateiformat: {path.suffix}")
    return writer(path, sheets)


def ensure_suffix(path: str, selected_filter: str) -> str:
    """Append the extension of the chosen filter when the user typed none."""
    if Path(path).suffix:
        return path
    m = re.search(r"\*(\.\w+)", selected_filter or "")
    return path + (m.group(1) if m else ".xlsx")


def open_file(path: str | Path) -> None:
    os.startfile(str(path))  # noqa: S606 - Windows only by design
