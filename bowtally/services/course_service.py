# -*- coding: utf-8 -*-
"""CRUD for course_targets and schedule_groups."""
from bowtally.database.engine import session_scope
from bowtally.database.models import CourseTarget, ScheduleGroup


# ---------------------------------------------------------------- course targets

def list_targets(tournament_id: int) -> list[CourseTarget]:
    with session_scope() as s:
        rows = (s.query(CourseTarget)
                .filter_by(tournament_id=tournament_id)
                .order_by(CourseTarget.sort_order, CourseTarget.id)
                .all())
        s.expunge_all()
        return rows


def save_target(data: dict, target_id: int | None, tournament_id: int) -> CourseTarget:
    with session_scope() as s:
        if target_id:
            t = s.get(CourseTarget, target_id)
        else:
            t = CourseTarget(tournament_id=tournament_id)
            s.add(t)
        for k, v in data.items():
            setattr(t, k, v or None if isinstance(v, str) else v)
        s.flush()
        s.expunge(t)
        return t


def delete_target(target_id: int) -> None:
    with session_scope() as s:
        t = s.get(CourseTarget, target_id)
        if t:
            s.delete(t)


def reorder_targets(tournament_id: int, ordered_ids: list[int]) -> None:
    with session_scope() as s:
        for i, tid in enumerate(ordered_ids):
            t = s.get(CourseTarget, tid)
            if t and t.tournament_id == tournament_id:
                t.sort_order = i


def copy_targets(from_tournament_id: int, to_tournament_id: int) -> None:
    """Copy all course_targets from one tournament to another (used when cloning)."""
    with session_scope() as s:
        rows = (s.query(CourseTarget)
                .filter_by(tournament_id=from_tournament_id)
                .order_by(CourseTarget.sort_order, CourseTarget.id)
                .all())
        for src in rows:
            s.add(CourseTarget(
                tournament_id=to_tournament_id,
                number=src.number,
                animal_name=src.animal_name,
                distance_m=src.distance_m,
                arrow_stop_class=src.arrow_stop_class,
                terrain_type=src.terrain_type,
                max_group_size=src.max_group_size,
                helper_note=src.helper_note,
                sort_order=src.sort_order,
            ))


# ---------------------------------------------------------------- schedule groups

def list_groups(tournament_id: int) -> list[ScheduleGroup]:
    with session_scope() as s:
        rows = (s.query(ScheduleGroup)
                .filter_by(tournament_id=tournament_id)
                .order_by(ScheduleGroup.start_time, ScheduleGroup.id)
                .all())
        s.expunge_all()
        return rows


def save_group(data: dict, group_id: int | None, tournament_id: int) -> ScheduleGroup:
    with session_scope() as s:
        if group_id:
            g = s.get(ScheduleGroup, group_id)
        else:
            g = ScheduleGroup(tournament_id=tournament_id)
            s.add(g)
        for k, v in data.items():
            setattr(g, k, v or None if isinstance(v, str) else v)
        s.flush()
        s.expunge(g)
        return g


def delete_group(group_id: int) -> None:
    with session_scope() as s:
        g = s.get(ScheduleGroup, group_id)
        if g:
            s.delete(g)
