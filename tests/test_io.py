# -*- coding: utf-8 -*-
from datetime import date

import pytest

from bowtally.io.exporter import write_sheets
from bowtally.io.importer import (ARCHER_IMPORT_FIELDS, auto_mapping, convert_rows,
                                  detect_separator, read_table)

HEADERS = ["Vorname", "Nachname", "Geburtsdatum", "Verein"]
ROWS = [["Anna", "Müller", date(1990, 5, 1), "BSV"], ["", "Ohne", None, None]]


@pytest.mark.parametrize("ext", [".csv", ".xlsx", ".ods"])
def test_roundtrip(tmp_path, ext):
    path = tmp_path / f"a{ext}"
    write_sheets(path, [("Schützen", HEADERS, ROWS)])
    headers, rows = read_table(path)
    assert headers == HEADERS
    mapping = auto_mapping(headers, ARCHER_IMPORT_FIELDS)
    records, errors = convert_rows(rows, mapping, ARCHER_IMPORT_FIELDS)
    assert records == [{"first_name": "Anna", "last_name": "Müller",
                        "birth_date": date(1990, 5, 1), "club": "BSV"}]
    assert errors == ["Zeile 3: Vorname fehlt"]


def test_separator():
    assert detect_separator("a;b;c\n1;2;3") == ";"
    assert detect_separator("a,b,c") == ","
