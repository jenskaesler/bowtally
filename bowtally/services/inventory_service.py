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


def delete_item(item_id: int) -> None:
    with session_scope() as s:
        item = s.get(InventoryItem, item_id)
        if item:
            s.delete(item)
