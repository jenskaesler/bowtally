# -*- coding: utf-8 -*-
from datetime import date, timedelta

import pytest
from sqlalchemy import select

from bowtally.database import engine
from bowtally.database.engine import session_scope
from bowtally.database.models import Member, MemberHelperHistory, Tournament
from bowtally.services import ValidationError
from bowtally.services import helper_service as hs
from bowtally.services import member_service as ms
from bowtally.services import master_data_service as md
from bowtally.services import scoring_service as sc
from bowtally.services import tournament_service as ts


@pytest.fixture(scope="module", autouse=True)
def db(tmp_path_factory):
    engine.init_database(f"sqlite:///{(tmp_path_factory.mktemp('db') / 'h.db').as_posix()}")


def _tournament(phase="scoring") -> int:
    ibo = next(r for r in sc.list_rules() if r.name.startswith("IBO"))
    t = ts.save_tournament({"name": "Helfer-Cup", "date": date.today() + timedelta(days=5),
                            "num_targets": 1, "scoring_rule_id": ibo.id},
                           [md.list_bow_classes()[0].id])
    with session_scope() as s:
        s.get(Tournament, t.id).phase = phase     # skip the lifecycle, only closing matters here
    return t.id


def _member(number, first="Anna", last="Muster", helper=True, active=True) -> int:
    with session_scope() as s:
        m = Member(member_number=number, first_name=first, last_name=last,
                   phone="123", email=f"{number}@x.de", is_tournament_helper=helper, active=active)
        s.add(m)
        s.flush()
        return m.id


def _history(member_id):
    with session_scope() as s:
        return s.scalars(select(MemberHelperHistory)
                         .where(MemberHelperHistory.member_id == member_id)).all()


def test_manual_helper_has_no_member_link():
    tid = _tournament()
    th = hs.create_manual(tid, {"first_name": " Max ", "last_name": "Mann", "task": "Kasse"})
    assert th.member_id is None
    assert hs.display_contact(th) == ("Mann, Max", "", "")
    with pytest.raises(ValidationError):
        hs.create_manual(tid, {"first_name": "", "last_name": "Mann"})


def test_assign_member_only_active_flagged_and_once():
    tid = _tournament()
    ok = _member("A1")
    with pytest.raises(ValidationError):
        hs.assign_member(tid, _member("A2", helper=False))
    with pytest.raises(ValidationError):
        hs.assign_member(tid, _member("A3", active=False))
    assert hs.assign_member(tid, ok).member_id == ok
    with pytest.raises(ValidationError):
        hs.assign_member(tid, ok)
    assert ok not in [m.id for m in hs.list_assignable_members(tid)]


def test_update_linked_helper_keeps_member_data():
    tid = _tournament()
    mid = _member("B1", first="Berta", last="Beispiel")
    th = hs.assign_member(tid, mid)
    hs.update_assignment(th.id, {"first_name": "Hacker", "last_name": "X", "phone": "999",
                                 "task": "Aufbau", "time_from": "08:00", "confirmed": True})
    got = hs.get_tournament_helper(th.id)
    assert (got.task, got.time_from, got.confirmed) == ("Aufbau", "08:00", True)
    assert got.first_name is None and hs.display_contact(got) == ("Beispiel, Berta", "123", "B1@x.de")
    with session_scope() as s:
        assert s.get(Member, mid).first_name == "Berta"


def test_close_writes_history_and_going_back_removes_only_auto_entries():
    tid = _tournament()
    with_times, no_times, bad_times = _member("C1"), _member("C2"), _member("C3")
    for mid, times in ((with_times, ("08:00", "10:30")), (no_times, (None, None)),
                       (bad_times, ("12:00", "10:00"))):
        th = hs.assign_member(tid, mid)
        hs.update_assignment(th.id, {"task": "Kasse", "time_from": times[0], "time_to": times[1]})
    hs.create_manual(tid, {"first_name": "Nur", "last_name": "Turnier"})
    with session_scope() as s:                       # manual history entry: no tournament link
        s.add(MemberHelperHistory(member_id=with_times, tournament_name="Altes Turnier"))

    assert ts.transition_phase(tid, "closed", force=True).ok
    entry = next(h for h in _history(with_times) if h.tournament_id == tid)
    assert (entry.tournament_name, entry.role, entry.hours) == ("Helfer-Cup", "Kasse", 2.5)
    assert entry.date == date.today() + timedelta(days=5)
    assert _history(no_times)[0].hours is None and _history(bad_times)[0].hours is None
    with session_scope() as s:                       # manual helper creates no history
        assert len(s.scalars(select(MemberHelperHistory).where(
            MemberHelperHistory.tournament_id == tid)).all()) == 3

    ts.transition_phase_backward(tid)
    assert ts.transition_phase(tid, "closed", force=True).ok       # re-closing: no duplicates
    assert len([h for h in _history(with_times) if h.tournament_id == tid]) == 1

    ts.transition_phase_backward(tid)
    assert [h.tournament_name for h in _history(with_times)] == ["Altes Turnier"]
    assert _history(no_times) == []


def _manual(mid, tid, **extra):
    return ms.add_history(mid, {"tournament_name": "Helfer-Cup", "tournament_id": tid, **extra})


def test_manual_entry_linked_to_a_tournament_can_be_edited_and_deleted():
    tid, other = _tournament(), _tournament()
    mid = _member("E1")
    entry = _manual(mid, tid, role="Kasse")
    assert entry.tournament_id == tid and ms.is_manual_entry(entry)
    ms.update_history(entry.id, {"tournament_name": "Neu", "tournament_id": other})
    assert _history(mid)[0].tournament_id == other
    with pytest.raises(ValidationError):
        ms.update_history(entry.id, {"tournament_name": "x", "tournament_id": 99999})
    ms.delete_history(entry.id)
    assert _history(mid) == []


def test_linking_the_same_tournament_twice_is_rejected():
    tid = _tournament()
    mid = _member("E2")
    _manual(mid, tid)
    with pytest.raises(ValidationError, match="bereits einen Eintrag"):
        _manual(mid, tid)
    assert _manual(mid, None) and _manual(mid, None)           # unlinked entries may repeat


def test_closing_keeps_a_manual_link_and_going_back_does_not_delete_it():
    tid = _tournament()
    mid, auto_mid = _member("E3"), _member("E4")
    manual = _manual(mid, tid, role="Handschriftlich")
    for m in (mid, auto_mid):
        hs.assign_member(tid, m)
    assert ts.transition_phase(tid, "closed", force=True).ok
    assert [h.role for h in _history(mid)] == ["Handschriftlich"]     # manual entry wins
    auto = _history(auto_mid)[0]
    assert not ms.is_manual_entry(auto)
    with pytest.raises(ValidationError):                              # auto entries stay locked
        ms.update_history(auto.id, {"tournament_name": "x"})
    with pytest.raises(ValidationError, match="bereits einen Eintrag"):
        _manual(auto_mid, tid)
    ts.transition_phase_backward(tid)
    assert [h.id for h in _history(mid)] == [manual.id] and _history(auto_mid) == []


def test_closing_twice_in_a_row_upserts():
    tid = _tournament()
    mid = _member("D1")
    hs.assign_member(tid, mid)
    for _ in range(2):
        with session_scope() as s:
            ts._write_helper_history(s, s.get(Tournament, tid))
    assert len(_history(mid)) == 1
