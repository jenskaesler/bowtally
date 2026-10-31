# -*- coding: utf-8 -*-
"""CRUD for score_sheet_templates."""
import json

from bowtally.database.engine import session_scope
from bowtally.database.models import ScoreSheetTemplate

TYPE_LABELS = {
    "3d": "3D",
    "field": "Feld",
    "indoor": "Halle",
    "blowpipe": "Blasrohr",
    "custom": "Benutzerdefiniert",
}


def list_templates() -> list[ScoreSheetTemplate]:
    with session_scope() as s:
        rows = s.query(ScoreSheetTemplate).order_by(
            ScoreSheetTemplate.is_builtin.desc(), ScoreSheetTemplate.name).all()
        s.expunge_all()
        return rows


def get_template(template_id: int) -> ScoreSheetTemplate | None:
    with session_scope() as s:
        t = s.get(ScoreSheetTemplate, template_id)
        if t:
            s.expunge(t)
        return t


def save_template(data: dict, template_id: int | None) -> ScoreSheetTemplate:
    with session_scope() as s:
        if template_id:
            t = s.get(ScoreSheetTemplate, template_id)
        else:
            t = ScoreSheetTemplate()
            s.add(t)
        t.name = data["name"]
        t.tournament_type = data.get("tournament_type", "custom")
        # column_config and header_fields are stored as JSON strings
        cols = data.get("column_config", [])
        t.column_config = json.dumps(cols) if isinstance(cols, list) else cols
        hdrs = data.get("header_fields", ["name", "bow_class", "start_number"])
        t.header_fields = json.dumps(hdrs) if isinstance(hdrs, list) else hdrs
        s.flush()
        s.expunge(t)
        return t


def delete_template(template_id: int) -> None:
    with session_scope() as s:
        t = s.get(ScoreSheetTemplate, template_id)
        if t and not t.is_builtin:
            s.delete(t)


def columns(template: ScoreSheetTemplate) -> list[dict]:
    try:
        return json.loads(template.column_config or "[]")
    except (ValueError, TypeError):
        return []


def header_fields(template: ScoreSheetTemplate) -> list[str]:
    try:
        return json.loads(template.header_fields or "[]")
    except (ValueError, TypeError):
        return ["name", "bow_class", "start_number"]
