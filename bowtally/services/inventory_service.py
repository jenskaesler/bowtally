# -*- coding: utf-8 -*-
"""CRUD-Service für Vereins-Inventar (Scheiben und 3D-Ziele)."""
from bowtally.database.models import InventoryItem
from bowtally.database.engine import session_scope
from bowtally.services import ValidationError

ITEM_TYPE_LABELS = {"target_face": "Scheibe", "3d_target": "3D-Ziel"}
CONDITION_LABELS = {"gut": "Gut", "mittel": "Mittel", "schlecht": "Schlecht"}


def list_items(item_type: str | None = None, active_only: bool = False):
    with session_scope() as s:
        q = s.query(InventoryItem)
        if item_type:
            q = q.filter_by(item_type=item_type)
        if active_only:
            q = q.filter_by(active=True)
        items = q.order_by(InventoryItem.name).all()
        s.expunge_all()
        return items


def save_item(data: dict, item_id: int | None = None) -> InventoryItem:
    name = (data.get("name") or "").strip()
    if not name:
        raise ValidationError("Bezeichnung darf nicht leer sein.")
    with session_scope() as s:
        if item_id:
            item = s.get(InventoryItem, item_id)
            if not item:
                raise ValidationError("Eintrag nicht gefunden.")
        else:
            item = InventoryItem()
            s.add(item)
        item.name = name
        item.item_type = data.get("item_type", "target_face")
        item.manufacturer = data.get("manufacturer") or None
        item.quantity = int(data.get("quantity") or 1)
        item.condition = data.get("condition") or None
        item.notes = data.get("notes") or None
        item.active = bool(data.get("active", True))
        s.flush()
        iid = item.id
    with session_scope() as s:
        item = s.get(InventoryItem, iid)
        s.expunge_all()
        return item


def import_items(records: list[dict], strategy: str, item_type: str) -> dict:
    """strategy: 'skip' | 'update' | 'new'. Returns counters."""
    result = {"created": 0, "updated": 0, "skipped": 0}
    with session_scope() as s:
        for rec in records:
            name = (rec.get("name") or "").strip()
            if not name:
                continue
            existing = (None if strategy == "new"
                        else s.query(InventoryItem).filter_by(name=name,
                                                              item_type=item_type).first())
            if existing is None:
                item = InventoryItem()
                item.name = name
                item.item_type = item_type
                item.manufacturer = rec.get("manufacturer") or None
                item.quantity = int(rec.get("quantity") or 1)
                item.condition = rec.get("condition") or None
                item.notes = rec.get("notes") or None
                item.active = bool(rec.get("active", True))
                s.add(item)
                result["created"] += 1
            elif strategy == "update":
                existing.manufacturer = rec.get("manufacturer") or existing.manufacturer
                existing.quantity = int(rec.get("quantity") or existing.quantity)
                existing.condition = rec.get("condition") or existing.condition
                existing.notes = rec.get("notes") or existing.notes
                if rec.get("active") is not None:
                    existing.active = bool(rec["active"])
                result["updated"] += 1
            else:
                result["skipped"] += 1
    return result


def delete_item(item_id: int) -> None:
    with session_scope() as s:
        item = s.get(InventoryItem, item_id)
        if item:
            s.delete(item)
