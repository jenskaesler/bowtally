# -*- coding: utf-8 -*-
"""CRUD for prizes; auto-assignment to ranking results after tournament close."""
from sqlalchemy.orm import joinedload

from bowtally.database.engine import session_scope
from bowtally.database.models import Prize


def _load(s, prize_id: int) -> Prize:
    return (s.query(Prize).options(joinedload(Prize.bow_class))
            .filter_by(id=prize_id).one())


def list_prizes(tournament_id: int) -> list[Prize]:
    with session_scope() as s:
        rows = (s.query(Prize).options(joinedload(Prize.bow_class))
                .filter_by(tournament_id=tournament_id)
                .order_by(Prize.sort_order, Prize.rank, Prize.id).all())
        s.expunge_all()
        return rows


def save_prize(data: dict, prize_id: int | None, tournament_id: int) -> Prize:
    with session_scope() as s:
        if prize_id:
            p = s.get(Prize, prize_id)
        else:
            p = Prize(tournament_id=tournament_id)
            s.add(p)
        p.rank = int(data["rank"])
        p.name = data["name"]
        p.description = data.get("description") or None
        p.value = float(data["value"]) if data.get("value") else None
        p.bow_class_id = data.get("bow_class_id") or None
        p.sort_order = data.get("sort_order", 0)
        s.flush()
        p = _load(s, p.id)
        s.expunge_all()
        return p


def delete_prize(prize_id: int) -> None:
    with session_scope() as s:
        p = s.get(Prize, prize_id)
        if p:
            s.delete(p)


def copy_prizes(from_tournament_id: int, to_tournament_id: int) -> None:
    with session_scope() as s:
        rows = (s.query(Prize).filter_by(tournament_id=from_tournament_id)
                .order_by(Prize.sort_order, Prize.rank).all())
        for src in rows:
            s.add(Prize(
                tournament_id=to_tournament_id,
                bow_class_id=src.bow_class_id,
                rank=src.rank,
                name=src.name,
                description=src.description,
                value=src.value,
                sort_order=src.sort_order,
            ))
