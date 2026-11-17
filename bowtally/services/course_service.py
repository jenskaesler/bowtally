# -*- coding: utf-8 -*-
"""CRUD for course_targets, course_items (inventory + one-off items) and schedule_groups."""
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from bowtally.database.engine import session_scope
from bowtally.database.models import CourseItem, CourseTarget, InventoryItem, ScheduleGroup
from bowtally.services import ValidationError


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
        for src in s.query(CourseItem).filter_by(tournament_id=from_tournament_id):
            s.add(CourseItem(
                tournament_id=to_tournament_id,
                inventory_item_id=src.inventory_item_id,
                name=src.name,
                quantity=src.quantity,
                unit_price=src.unit_price,
                is_one_off=src.is_one_off,
                sort_order=src.sort_order,
            ))


# ---------------------------------------------------------------- course items (inventory + one-off)

def list_course_items(tournament_id: int) -> list[CourseItem]:
    with session_scope() as s:
        return list(s.scalars(select(CourseItem).options(selectinload(CourseItem.inventory_item))
                              .where(CourseItem.tournament_id == tournament_id)
                              .order_by(CourseItem.sort_order, CourseItem.id)))


def save_course_item(data: dict, item_id: int | None = None,
                     tournament_id: int | None = None) -> CourseItem:
    """data: inventory_item_id (inventory item) or is_one_off + name + unit_price (one-off item)."""
    quantity = int(data.get("quantity") or 0)
    if quantity < 1:
        raise ValidationError("Die Menge muss mindestens 1 sein.")
    with session_scope() as s:
        item = s.get(CourseItem, item_id) if item_id else CourseItem(tournament_id=tournament_id)
        if item is None:
            raise ValidationError("Posten nicht gefunden.")
        inventory = s.get(InventoryItem, data["inventory_item_id"]) \
            if data.get("inventory_item_id") else None
        if inventory is not None:
            item.inventory_item_id, item.name = inventory.id, inventory.name
            item.unit_price, item.is_one_off = inventory.unit_price, False
        else:
            name = (data.get("name") or "").strip()
            if not name:
                raise ValidationError("Bezeichnung darf nicht leer sein.")
            item.inventory_item_id, item.name, item.is_one_off = None, name, True
            item.unit_price = float(data.get("unit_price") or 0)
            if item.unit_price < 0:
                raise ValidationError("Der Preis darf nicht negativ sein.")
        item.quantity = quantity
        s.add(item)
        s.flush()
        s.refresh(item, ["inventory_item"])
        return item


def delete_course_item(item_id: int) -> None:
    with session_scope() as s:
        item = s.get(CourseItem, item_id)
        if item:
            s.delete(item)


def stock_shortfall(item: CourseItem) -> int:
    """Units missing in stock for an inventory item (0 for one-off items)."""
    if item.inventory_item is None:
        return 0
    return max(0, item.quantity - item.inventory_item.quantity)


def one_off_cost(tournament_id: int) -> float:
    return round(sum(i.quantity * i.unit_price for i in list_course_items(tournament_id)
                     if i.is_one_off), 2)


def stock_goods_value(tournament_id: int) -> float:
    """Requested quantity x current unit price of the inventory items used (not the whole stock)."""
    return round(sum(i.quantity * (i.inventory_item.unit_price if i.inventory_item else i.unit_price)
                     for i in list_course_items(tournament_id) if not i.is_one_off), 2)


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
