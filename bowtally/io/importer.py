# -*- coding: utf-8 -*-
"""Read CSV/XLSX/ODS tables, map columns to fields, validate and convert rows."""
import csv
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

FILE_FILTER = "Tabellen (*.csv *.xlsx *.ods);;CSV (*.csv);;Excel (*.xlsx);;OpenDocument (*.ods)"
PREVIEW_ROWS = 10


@dataclass
class ImportField:
    key: str
    label: str
    required: bool = False
    type: str = "str"                     # str | int | float | date | bool
    aliases: list[str] = field(default_factory=list)


ARCHER_IMPORT_FIELDS = [
    ImportField("first_name", "Vorname", True, aliases=["firstname", "first name"]),
    ImportField("last_name", "Nachname", True, aliases=["name", "lastname", "last name"]),
    ImportField("birth_date", "Geburtsdatum", type="date", aliases=["geburtstag", "birthday"]),
    ImportField("club", "Verein", aliases=["club"]),
    ImportField("member_number", "Mitgliedsnummer", aliases=["mitgliedsnr", "mitglieds-nr",
                                                             "member number", "passnummer"]),
    ImportField("email", "E-Mail", aliases=["email", "mail"]),
    ImportField("phone", "Telefon", aliases=["phone", "tel"]),
    ImportField("default_bow_class", "Bogenklasse", aliases=["klasse", "bow class"]),
    ImportField("notes", "Notizen", aliases=["bemerkung", "notes"]),
]

PARTICIPANT_IMPORT_FIELDS = [
    f for f in ARCHER_IMPORT_FIELDS if f.key != "default_bow_class"
] + [
    ImportField("bow_class", "Bogenklasse", aliases=["klasse", "bow class"]),
    ImportField("start_number", "Startnummer", type="int", aliases=["startnr", "start-nr",
                                                                     "nr"]),
    ImportField("start_group", "Startgruppe", aliases=["gruppe", "group"]),
]

MEMBER_IMPORT_FIELDS = [
    ImportField("member_number", "Mitgliedsnummer", aliases=["mitgliedsnr", "mitglieds-nr",
                                                             "member number"]),
    ImportField("first_name", "Vorname", True, aliases=["firstname", "first name"]),
    ImportField("last_name", "Nachname", True, aliases=["name", "lastname", "last name"]),
    ImportField("street", "Straße", aliases=["strasse", "street"]),
    ImportField("postal_code", "PLZ", aliases=["postleitzahl", "postal code"]),
    ImportField("city", "Ort", aliases=["stadt", "city"]),
    ImportField("phone", "Telefon", aliases=["phone", "tel"]),
    ImportField("email", "E-Mail", aliases=["email", "mail"]),
    ImportField("member_since", "Mitglied seit", type="date", aliases=["eintritt", "member since"]),
    ImportField("notes", "Notizen", aliases=["bemerkung", "notes"]),
]

BOW_CLASS_IMPORT_FIELDS = [
    ImportField("name", "Bezeichnung", True, aliases=["bogenklasse", "bow class"]),
    ImportField("abbreviation", "Kürzel", True, aliases=["kürzel", "abbreviation", "short"]),
    ImportField("age_group", "Altersgruppe", aliases=["altersgruppe", "age group", "age_group"]),
    ImportField("description", "Beschreibung", aliases=["beschreibung", "description"]),
]

RULE_IMPORT_FIELDS = [      # same order as scoring_service.RULE_EXPORT_HEADERS
    ImportField("name", "Bezeichnung", True, aliases=["regelwerk", "rule"]),
    ImportField("description", "Beschreibung", aliases=["description"]),
    ImportField("discipline", "Disziplin", aliases=["discipline"]),
    ImportField("max_shots_per_target", "Schüsse je Ziel", type="int",
                aliases=["max_shots_per_target", "schüsse/scheibe", "schüsse"]),
    ImportField("allow_retry_shot", "Nachschuss", type="bool", aliases=["allow_retry_shot"]),
    ImportField("ring_values", "Zonen", required=True, aliases=["ring_values", "zonen (json)"]),
    ImportField("count_kill", "Kills zählen", type="bool"),
    ImportField("tie_kill", "Bei Gleichstand zählen Kills", type="bool"),
    ImportField("count_x", "X-Treffer zählen", type="bool"),
    ImportField("tie_x", "Bei Gleichstand zählen X-Treffer", type="bool"),
    ImportField("top_hits", "Treffer in der höchsten Wertung", type="bool"),
    ImportField("top_first", "Treffer in der höchsten Wertung zuerst", type="bool"),
    ImportField("shoot_off", "Stechen erforderlich", type="bool"),
]

INVENTORY_IMPORT_FIELDS = [
    ImportField("name", "Bezeichnung", True, aliases=["bezeichnung", "name"]),
    ImportField("category", "Kategorie", aliases=["category"]),
    ImportField("size", "Größe", aliases=["groesse", "size", "maße", "masse"]),
    ImportField("shop_url", "Link zum Shop", aliases=["shop-link", "shop", "link", "url"]),
    ImportField("unit_price", "Einzelpreis", True, type="float", aliases=["preis", "price"]),
    ImportField("quantity", "Anzahl", type="int", aliases=["quantity", "menge", "bestand"]),
    ImportField("use_in_course", "Parcoursplanung", type="bool",
                aliases=["für parcoursplanung", "parcours"]),
    ImportField("active", "Aktiv", type="bool", aliases=["active"]),
    ImportField("notes", "Notizen", aliases=["bemerkung", "notes"]),
]

DUPLICATE_STRATEGIES = {"skip": "Überspringen", "update": "Aktualisieren", "new": "Immer neu"}


# ---------------------------------------------------------------- reading

def detect_separator(sample: str) -> str:
    first = sample.splitlines()[0] if sample else ""
    return ";" if first.count(";") >= first.count(",") and ";" in first else ","


def _read_csv(path: Path) -> list[list]:
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "cp1252"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    return list(csv.reader(text.splitlines(), delimiter=detect_separator(text)))


def _read_xlsx(path: Path) -> list[list]:
    from openpyxl import load_workbook
    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        return [list(r) for r in wb.worksheets[0].iter_rows(values_only=True)]
    finally:
        wb.close()


def _read_ods(path: Path) -> list[list]:
    from odf import teletype
    from odf.opendocument import load
    from odf.table import Table, TableCell, TableRow
    doc = load(str(path))
    table = doc.spreadsheet.getElementsByType(Table)[0]
    rows = []
    for tr in table.getElementsByType(TableRow):
        row = []
        for cell in tr.getElementsByType(TableCell):
            rep = int(cell.getAttribute("numbercolumnsrepeated") or 1)
            vtype = cell.getAttribute("valuetype")
            if vtype == "float":
                v = float(cell.getAttribute("value"))
                value = int(v) if v.is_integer() else v
            elif vtype == "date":
                value = cell.getAttribute("datevalue")
            else:
                value = teletype.extractText(cell) or None
            row += [value] * (rep if value is not None else min(rep, 64))
        rows.append(row)
    return rows


def read_table(path: str | Path) -> tuple[list[str], list[list]]:
    """Returns (headers, data rows). Empty rows and trailing empty cells are dropped."""
    path = Path(path)
    ext = path.suffix.lower()
    reader = {".csv": _read_csv, ".xlsx": _read_xlsx, ".ods": _read_ods}.get(ext)
    if reader is None:
        raise ValueError(f"Nicht unterstütztes Dateiformat: {ext}")
    rows = []
    for r in reader(path):
        r = ["" if v is None else v for v in r]
        while r and r[-1] == "":
            r.pop()
        if r:
            rows.append(r)
    if not rows:
        return [], []
    headers = [str(h).strip() for h in rows[0]]
    width = len(headers)
    return headers, [(r + [""] * width)[:width] for r in rows[1:]]


# ---------------------------------------------------------------- mapping

def auto_mapping(headers: list[str], fields: list[ImportField]) -> dict[str, int | None]:
    norm = [h.strip().lower() for h in headers]
    mapping = {}
    for f in fields:
        names = [f.label.lower(), f.key.lower()] + f.aliases
        mapping[f.key] = next((norm.index(n) for n in names if n in norm), None)
    return mapping


def parse_date(value) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d.%m.%y", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"ungültiges Datum '{text}'")


def _convert(value, ftype: str):
    if value in (None, ""):
        return None
    if ftype == "int":
        try:
            return int(float(str(value).replace(",", ".")))
        except ValueError:
            raise ValueError(f"keine Zahl '{value}'") from None
    if ftype == "float":
        try:
            return float(str(value).replace(",", "."))
        except ValueError:
            raise ValueError(f"keine Zahl '{value}'") from None
    if ftype == "date":
        return parse_date(value)
    if ftype == "bool":
        return str(value).strip().lower() in ("1", "true", "ja", "yes", "x")
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).strip() or None


def convert_rows(rows: list[list], mapping: dict[str, int | None],
                 fields: list[ImportField]) -> tuple[list[dict], list[str]]:
    """Validate + convert. Returns (valid records, error messages with row numbers)."""
    records, errors = [], []
    for line_no, row in enumerate(rows, start=2):   # line 1 = header
        rec, row_errors = {}, []
        for f in fields:
            col = mapping.get(f.key)
            raw = row[col] if col is not None and col < len(row) else None
            try:
                value = _convert(raw, f.type)
            except ValueError as e:
                row_errors.append(f"{f.label}: {e}")
                continue
            if f.required and value is None:
                row_errors.append(f"{f.label} fehlt")
            if col is not None:
                rec[f.key] = value
        if row_errors:
            errors.append(f"Zeile {line_no}: " + "; ".join(row_errors))
        else:
            records.append(rec)
    return records, errors


def missing_required(mapping: dict[str, int | None], fields: list[ImportField]) -> list[str]:
    return [f.label for f in fields if f.required and mapping.get(f.key) is None]
