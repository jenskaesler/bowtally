# -*- coding: utf-8 -*-
import pytest

from bowtally.database import engine
from bowtally.io.importer import RULE_IMPORT_FIELDS, convert_rows
from bowtally.services import ValidationError
from bowtally.services import scoring_service as sc

ZONES = [{"zone": "Kill-Zone", "points": 11, "type": "kill"}, {"zone": "Körper", "points": 8},
         {"zone": "Miss", "points": 0, "type": "miss"}]


@pytest.fixture(autouse=True)
def db(tmp_path):
    engine.init_database(f"sqlite:///{(tmp_path / 'x.db').as_posix()}")


def _roundtrip(rule, strategy="new", name=None):
    """Export the rule to a table and import that table again, like a user would."""
    headers, row = sc.RULE_EXPORT_HEADERS, sc.rule_export_row(rule)
    if name:
        row = [name] + row[1:]
    mapping = {f.key: i for i, f in enumerate(RULE_IMPORT_FIELDS)}
    records, errors = convert_rows([row], mapping, RULE_IMPORT_FIELDS)
    assert errors == [] and len(headers) == len(RULE_IMPORT_FIELDS)
    return sc.import_rules(records, strategy)


def test_zones_are_written_and_read_as_plain_text():
    text = sc.format_zones(ZONES)
    assert text == "Kill-Zone = 11 [Kill]; Körper = 8; Miss = 0 [Miss]"
    assert sc.parse_zones(text) == ZONES
    assert sc.parse_zones("Treffer=5;Fehl=0[miss]") == [{"zone": "Treffer", "points": 5},
                                                         {"zone": "Fehl", "points": 0, "type": "miss"}]
    for bad in ("Treffer", "Treffer = viel", "A = 5 [Unbekannt]"):
        with pytest.raises(ValidationError):
            sc.parse_zones(bad)


def test_builtin_rule_exports_readable_columns_without_json():
    hunter = next(r for r in sc.list_rules() if r.name == "3D Hunter (IBO)")
    row = dict(zip(sc.RULE_EXPORT_HEADERS, sc.rule_export_row(hunter)))
    assert row["Disziplin"] == "3D-Parcours"
    assert (row["Kills zählen"], row["Bei Gleichstand zählen Kills"]) == ("Ja", "Ja")
    assert (row["X-Treffer zählen"], row["Treffer in der höchsten Wertung"]) == ("Nein", "Ja")
    assert not any("{" in str(v) or "[{" in str(v) for v in row.values())
    assert " = " in row["Zonen"]


def test_export_then_import_keeps_zones_counters_and_tie_break():
    parcours = sc.save_rule({"name": "Eigenes 3D", "ring_values": ZONES, "max_shots_per_target": 2,
                             "allow_retry_shot": True, "description": "Beschreibung",
                             "tracked_specials": [], "rules_json": {"discipline": "3d"}})
    options = sc.rule_options_to_data("3d", {"count_kill": True, "tie_kill": True, "top_hits": True,
                                             "top_first": True, "shoot_off": True}, ZONES)
    sc.save_rule({"name": "Eigenes 3D", "ring_values": ZONES, "max_shots_per_target": 2,
                  "allow_retry_shot": True, "description": "Beschreibung", **options}, parcours.id)
    parcours = sc.get_rule(parcours.id)

    assert _roundtrip(parcours, name="Kopie 3D") == {"created": 1, "updated": 0, "skipped": 0}
    copy = next(r for r in sc.list_rules() if r.name == "Kopie 3D")
    assert (copy.ring_values, copy.max_shots_per_target, copy.allow_retry_shot,
            copy.description) == (ZONES, 2, True, "Beschreibung")
    assert sc.rule_discipline(copy) == "3d"
    assert [(sp["key"], sp["tiebreak"]) for sp in sc.counter_specials(copy)] == [("kill", True)]
    assert (copy.rules_json["tiebreak"], copy.rules_json["top_hits_first"],
            copy.rules_json["shoot_off"]) == ("most_top_scores", True, True)


def test_import_accepts_old_files_with_json_zones_and_old_headers():
    records = [{"name": "Alt", "ring_values": '[{"zone": "Mitte", "points": 10, "type": "x"}]',
                "max_shots_per_target": 1}]
    assert sc.import_rules(records, "new")["created"] == 1
    old = next(r for r in sc.list_rules() if r.name == "Alt")
    assert old.ring_values == [{"zone": "Mitte", "points": 10, "type": "x"}]
    old_headers = ["Bezeichnung", "Beschreibung", "Schüsse/Scheibe", "Nachschuss", "Zonen (JSON)"]
    from bowtally.io.importer import auto_mapping
    mapping = auto_mapping(old_headers, RULE_IMPORT_FIELDS)
    assert mapping["max_shots_per_target"] == 2 and mapping["ring_values"] == 4
