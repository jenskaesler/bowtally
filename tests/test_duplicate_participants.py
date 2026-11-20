# -*- coding: utf-8 -*-
"""A person takes part in a tournament only once: same archer (database id) or same name.
The pass number is optional and only identifies an archer together with the name."""
from datetime import date

import pytest
import sqlalchemy

from bowtally.database import engine
from bowtally.database.engine import session_scope
from bowtally.database.models import TournamentParticipant
from bowtally.services import ValidationError
from bowtally.services import master_data_service as md
from bowtally.services import participant_service as ps
from bowtally.services import scoring_service as sc
from bowtally.services import tournament_service as ts


@pytest.fixture(autouse=True)
def db(tmp_path):
    engine.init_database(f"sqlite:///{(tmp_path / 'd.db').as_posix()}")


def _tournament():
    ibo = next(r for r in sc.list_rules() if r.name.startswith("IBO"))
    classes = md.list_bow_classes()
    t = ts.save_tournament({"name": "Doppelt", "date": date(2027, 6, 1), "num_targets": 2,
                            "scoring_rule_id": ibo.id}, [c.id for c in classes[:2]])
    assert ts.transition_phase(t.id, "announcement").ok
    return ts.get_tournament(t.id)


def _names(tid):
    return sorted(f"{p.archer.first_name} {p.archer.last_name}"
                  for p in ts.get_tournament(tid).participants)


def test_same_archer_id_and_same_name_are_added_once():
    t = _tournament()
    anna = md.save_archer({"first_name": "Anna", "last_name": "Alt"})
    anna_again = md.save_archer({"first_name": " anna ", "last_name": "ALT"})  # second record
    assert ts.add_participants(t.id, [anna.id, anna.id, anna_again.id]) == 1
    assert ts.add_participants(t.id, [anna_again.id]) == 0
    assert _names(t.id) == ["Anna Alt"]


def test_same_name_with_different_birth_dates_are_two_persons():
    t = _tournament()
    senior = md.save_archer({"first_name": "Max", "last_name": "Muster",
                             "birth_date": date(1960, 1, 1)})
    junior = md.save_archer({"first_name": "Max", "last_name": "Muster",
                             "birth_date": date(2005, 1, 1)})
    assert ts.add_participants(t.id, [senior.id, junior.id]) == 2


def test_pass_number_alone_does_not_make_a_duplicate():
    t = _tournament()
    md.save_archer({"first_name": "Anna", "last_name": "Alt", "pass_number": "P1"})
    # same pass number but another name (typo in the list): a different person
    r = ts.import_participants(t.id, [{"first_name": "Bert", "last_name": "Bach",
                                       "pass_number": "P1"}], "skip")
    assert r["added"] == 1 and r["created"] == 1
    assert _names(t.id) == ["Bert Bach"]


def test_import_skips_names_already_in_the_tournament_and_twice_in_the_file():
    t = _tournament()
    ts.add_participants(t.id, [md.save_archer({"first_name": "Anna", "last_name": "Alt"}).id])
    records = [{"first_name": "Anna", "last_name": "Alt"},          # already participant
               {"first_name": "Carl", "last_name": "Cord"},
               {"first_name": "carl", "last_name": "cord"}]         # twice in the file
    assert ts.import_capacity_error(t.id, records, "new") is None
    r = ts.import_participants(t.id, records, "new")
    assert (r["added"], r["duplicates"], r["created"]) == (1, 2, 1)   # no duplicate master record
    assert _names(t.id) == ["Anna Alt", "Carl Cord"]


def test_walk_in_with_the_name_of_a_participant_is_refused():
    t = _tournament()
    ts.add_participants(t.id, [md.save_archer({"first_name": "Anna", "last_name": "Alt"}).id])
    with pytest.raises(ValidationError, match="bereits Teilnehmer"):
        ps.register_walk_in(t.id, {"first_name": "ANNA", "last_name": "alt"},
                            t.bow_classes[0].id, None, paid=False)


def test_database_refuses_the_same_archer_twice():
    t = _tournament()
    archer = md.save_archer({"first_name": "Anna", "last_name": "Alt"})
    ts.add_participants(t.id, [archer.id])
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        with session_scope() as s:
            s.add(TournamentParticipant(tournament_id=t.id, archer_id=archer.id))
