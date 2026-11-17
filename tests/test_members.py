# -*- coding: utf-8 -*-
from datetime import date, timedelta

import pytest

from bowtally.database import engine
from bowtally.database.models import TournamentHelper
from bowtally.services import ValidationError
from bowtally.services import member_service as ms
from bowtally.services import master_data_service as md, scoring_service
from bowtally.services import tournament_service as ts


@pytest.fixture(autouse=True)
def db(tmp_path):
    engine.init_database(f"sqlite:///{(tmp_path / 't.db').as_posix()}")


def _member(**extra):
    data = {"member_number": "1", "first_name": "Anna", "last_name": "Alt", **extra}
    return ms.create_member(data)


def _tournament():
    rule = scoring_service.list_rules()[0]
    return ts.save_tournament({"name": "T", "date": date(2026, 5, 1), "num_targets": 1,
                               "shots_per_target": 1, "scoring_rule_id": rule.id},
                              [md.list_bow_classes()[0].id])


def test_iban_check():
    assert ms.is_valid_iban("") and ms.is_valid_iban("DE89 3704 0044 0532 0130 00")
    assert not ms.is_valid_iban("DE89 3704 0044 0532 0130 01") and not ms.is_valid_iban("DE89")


def test_create_update_and_validation():
    assert ms.next_member_number() == "1"
    m = _member(iban="de89 3704 0044 0532 0130 00")
    assert m.iban == "DE89370400440532013000" and ms.next_member_number() == "2"
    ms.update_member(m.id, {"member_number": "1", "first_name": "Anne", "last_name": "Alt"})
    assert ms.get_member(m.id).first_name == "Anne"
    for bad in ({"member_number": "1"},                    # duplicate number
                {"member_number": "2", "first_name": ""},
                {"member_number": "2", "email": "kein-mail"},
                {"member_number": "2", "iban": "DE00 1234"}):
        with pytest.raises(ValidationError):
            ms.create_member({"first_name": "B", "last_name": "B", **bad})


def test_status_independent_of_active_flag():
    past, future = date.today() - timedelta(days=1), date.today() + timedelta(days=1)
    assert ms.member_status(_member(cancelled_on=past, active=True)) == "Gekündigt"
    assert ms.member_status(_member(member_number="2", cancelled_on=future, active=False)) == "Aktiv"


def test_manual_history_entries_only():
    m = _member()
    h = ms.add_history(m.id, {"tournament_name": "Alt-Turnier", "date": date(2020, 5, 1),
                              "role": "Kasse", "hours": 2.5})
    ms.update_history(h.id, {"tournament_name": "Alt-Turnier", "hours": 3.0})
    assert [e.hours for e in ms.list_history(m.id)] == [3.0]
    with pytest.raises(ValidationError):
        ms.add_history(m.id, {"tournament_name": " "})
    ms.delete_history(h.id)
    assert ms.list_history(m.id) == []


def test_automatic_history_is_read_only():
    from bowtally.database.engine import session_scope
    from bowtally.database.models import MemberHelperHistory
    m = _member()
    t = _tournament()
    with session_scope() as s:
        entry = MemberHelperHistory(member_id=m.id, tournament_id=t.id, tournament_name="T")
        s.add(entry)
        s.flush()
        entry_id = entry.id
    with pytest.raises(ValidationError):
        ms.delete_history(entry_id)


def test_delete_refused_with_assignments():
    from bowtally.database.engine import session_scope
    m = _member()
    t = _tournament()
    with session_scope() as s:
        s.add(TournamentHelper(tournament_id=t.id, member_id=m.id))
    with pytest.raises(ValidationError):
        ms.delete_member(m.id)
    other = _member(member_number="2", first_name="B")
    ms.delete_member(other.id)
    assert [x.id for x in ms.list_members()] == [m.id]


def test_import_matches_by_number_then_name_and_ignores_bank_fields():
    _member(first_name="Anna", last_name="Alt")
    records = [{"member_number": "1", "first_name": "Anna", "last_name": "Alt", "city": "Ulm",
                "iban": "DE89370400440532013000"},
               {"first_name": "Neu", "last_name": "Mitglied"}]
    assert ms.import_members(records, "skip") == {"created": 1, "updated": 0, "skipped": 1}
    assert ms.import_members(records, "overwrite") == {"created": 0, "updated": 2, "skipped": 0}
    anna = ms.list_members()[0]
    assert anna.city == "Ulm"
    assert {m.member_number for m in ms.list_members()} == {"1", "2"}
