# -*- coding: utf-8 -*-
from datetime import date, timedelta

import pytest

from bowtally.database import engine
from bowtally.services import ValidationError
from bowtally.services import master_data_service as md
from bowtally.services import participant_service as ps
from bowtally.services import scoring_service as sc
from bowtally.services import tournament_service as ts


@pytest.fixture(scope="module", autouse=True)
def db(tmp_path_factory):
    engine.init_database(f"sqlite:///{(tmp_path_factory.mktemp('db') / 'l.db').as_posix()}")


def _tournament(**extra):
    ibo = next(r for r in sc.list_rules() if r.name.startswith("IBO"))
    classes = md.list_bow_classes()
    data = {"name": "Lifecycle", "date": date.today() + timedelta(days=30), "num_targets": 2,
            "scoring_rule_id": ibo.id, **extra}
    return ts.save_tournament(data, [classes[0].id, classes[1].id])


def _go(t, phase, force=True):
    res = ts.transition_phase(t.id, phase, force=force)
    assert res.ok, (phase, res)
    return res


def test_fee_templates_copied_and_protected():
    t = _tournament()
    assert [(f.name, f.amount) for f in t.fees] == [("Erwachsene", 20.0),
                                                     ("Schüler und Jugendliche", 10.0)]
    assert all(f.tournament_id is None for f in ts.list_fee_templates())
    a = md.save_archer({"first_name": "Fee", "last_name": "User"})
    ts.add_participants(t.id, [a.id])
    pid = ts.get_tournament(t.id).participants[0].id
    ps.set_entry_fee(pid, t.fees[0].id)
    with pytest.raises(ValidationError):
        ts.delete_fee(t.fees[0].id)
    ts.delete_fee(t.fees[1].id)
    assert len(ts.list_fees(t.id)) == 1
    assert ts.load_fee_templates(t.id) == 2


def test_full_lifecycle_with_blockers_and_warnings():
    t = _tournament()
    # announcement -> preparation: only warnings (contact, bank, announcement)
    res = ts.transition_phase(t.id, "preparation")
    assert not res.ok and not res.errors and len(res.warnings) == 3
    assert ts.transition_phase(t.id, "registration").errors        # skipping not allowed
    _go(t, "preparation")
    log = ts.list_phase_log(t.id)
    assert log[-1].forced and len(log[-1].warnings_at_transition) == 3

    # preparation -> registration: deadline is a blocker, even with force
    res = ts.transition_phase(t.id, "registration", force=True)
    assert res.errors == ["Anmeldefrist nicht gesetzt"]
    ts.update_tournament_fields(t.id, {"registration_deadline": date.today(),
                                       "max_participants": 3})
    _go(t, "registration")

    archers = [md.save_archer({"first_name": f"P{i}", "last_name": "L"}).id for i in range(4)]
    with pytest.raises(ValidationError):                           # 4 > max 3
        ts.add_participants(t.id, archers)
    assert ts.add_participants(t.id, archers[:3]) == 3
    cap = ps.get_capacity_info(t.id)
    assert cap.is_full and cap.free_slots == 0 and cap.percentage == 100
    assert not ts.is_registration_open(t.id)

    # registration -> checkin: needs confirmed participants
    assert ts.transition_phase(t.id, "checkin", force=True).errors
    parts = sorted(ts.get_tournament(t.id).participants, key=lambda p: p.start_number)
    fee = ts.get_tournament(t.id).fees[0]
    for p in parts:
        ps.set_entry_fee(p.id, fee.id)
    assert ps.bulk_confirm([p.id for p in parts]) == 3
    assert ps.bulk_mark_paid([parts[0].id]) == 1
    rev = ts.get_revenue_summary(t.id)
    assert (rev.expected, rev.received, rev.outstanding) == (60.0, 20.0, 40.0)
    assert [(r.name, r.count, r.total) for r in rev.rows][0] == ("Erwachsene", 3, 60.0)
    res = ts.transition_phase(t.id, "checkin")
    assert "2 Teilnehmer haben noch nicht bezahlt" in res.warnings
    _go(t, "checkin")

    # checkin -> shooting: needs someone checked in; withdrawn frees capacity
    assert ts.transition_phase(t.id, "shooting", force=True).errors
    ps.checkin(parts[0].id)
    ps.checkin(parts[1].id)
    ps.set_registration_status(parts[2].id, "withdrawn")
    assert ps.get_capacity_info(t.id).active_count == 2
    found = ps.search_for_checkin(t.id, "p1")
    assert [p.archer.first_name for p in found] == ["P1"]
    assert [p.id for p in ps.search_for_checkin(t.id, str(parts[0].start_number))] == \
        [parts[0].id]
    _go(t, "shooting")
    assert ts.get_tournament(t.id).status == "active"

    # shooting -> scoring: needs scores; completion progress
    assert ts.transition_phase(t.id, "scoring", force=True).errors
    sc.set_score(parts[0].id, 1, 1, (20, None))
    sc.set_score(parts[0].id, 2, 1, (10, None))
    sc.set_score(parts[1].id, 1, 1, (5, None))
    prog = ts.get_completion_progress(t.id)
    assert (prog.entered, prog.needed) == (3, 4) and prog.incomplete_ids == [parts[1].id]
    res = ts.transition_phase(t.id, "scoring")
    assert res.warnings == ["1 Teilnehmer haben unvollständige Scheibenergebnisse"]
    _go(t, "scoring")

    # scoring -> closed: warnings only; afterwards everything is locked
    ts.mark_results_generated(t.id)
    res = ts.transition_phase(t.id, "closed")
    assert res.warnings == ["1 Teilnehmer haben noch nicht bezahlt"]
    _go(t, "closed")
    assert ts.get_tournament(t.id).status == "closed"
    with pytest.raises(ValidationError):
        sc.set_score(parts[0].id, 1, 1, (5, None))
    with pytest.raises(ValidationError):
        ps.checkin(parts[1].id)
    assert [e.to_phase for e in ts.list_phase_log(t.id)] == ts.PHASES[1:]


def test_announcement_outdated_and_past_date_blocker():
    t = _tournament(date=date.today() - timedelta(days=1))
    assert "Das Turnierdatum liegt in der Vergangenheit" in \
        ts.transition_phase(t.id, "preparation", force=True).errors
    ts.mark_announcement_generated(t.id)
    t = ts.get_tournament(t.id)
    first = t.announced_at
    assert not ts.announcement_outdated(t)
    ts.update_tournament_fields(t.id, {"contact_name": "Jens"})
    assert ts.announcement_outdated(ts.get_tournament(t.id))
    ts.mark_announcement_generated(t.id)
    t = ts.get_tournament(t.id)
    assert t.announced_at == first and not ts.announcement_outdated(t)


def test_import_capacity_and_walk_in():
    t = _tournament(max_participants=2)
    records = [{"first_name": f"I{i}", "last_name": "Imp"} for i in range(3)]
    assert "Nur noch 2 Plätze verfügbar, Import würde 3" in \
        ts.import_capacity_error(t.id, records, "skip")
    with pytest.raises(ValidationError):
        ts.import_participants(t.id, records, "skip")
    assert ts.import_participants(t.id, records[:1], "skip")["added"] == 1
    p = ps.register_walk_in(t.id, {"first_name": "Walk", "last_name": "In"},
                            t.bow_classes[0].id, t.fees[0].id, paid=True)
    assert p.registration_status == "checked_in" and p.payment_status == "paid"
    assert p.fee_amount_paid == 20.0
    with pytest.raises(ValidationError):                            # full now
        ps.register_walk_in(t.id, {"first_name": "Zu", "last_name": "Spät"},
                            t.bow_classes[0].id, None, paid=False)


def test_checklist():
    t = _tournament()
    ts.set_checklist_item(t.id, "parcours_ready", True)
    ts.set_checklist_item(t.id, ts.CHECKLIST_NOTES_KEY, "Anna: Kasse")
    assert ts.get_checklist_state(t.id) == {"parcours_ready": True,
                                            "helpers_notes": "Anna: Kasse"}


def test_announcement_pdf(tmp_path):
    from bowtally.reports.announcement import generate_announcement_pdf, split_info
    t = _tournament(registration_deadline=date.today() + timedelta(days=10),
                    max_participants=130, checkin_start_time="09:00",
                    shooting_start_time="10:00", practice_location="Wiese am Parkplatz",
                    bank_account_holder="BSV", bank_iban="DE00 1234", bank_bic="ABCDEF",
                    bank_reference_template="3D Turnier, {name}, {bow_class}",
                    contact_name="Jens", contact_email="a@b.de",
                    legal_notes="Teilnahme auf eigene Gefahr\nJeder haftet",
                    additional_info="Herzliche Einladung!\n\nWir freuen uns!")
    assert split_info(t.additional_info) == ("Herzliche Einladung!", "Wir freuen uns!")
    out = generate_announcement_pdf(t.id, tmp_path / "a.pdf")
    assert out.read_bytes()[:4] == b"%PDF"
    assert ts.get_tournament(t.id).announced_at is not None
