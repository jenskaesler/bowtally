# -*- coding: utf-8 -*-
"""Vereinsinventar: Kategorien, Artikel, Dateien und Instandhaltungen."""
import re
import shutil
import uuid
from datetime import date
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from bowtally import config
from bowtally.database.engine import session_scope
from bowtally.database.models import (InventoryCategory, InventoryFile, InventoryItem,
                                      InventoryRepair)
from bowtally.services import ValidationError

FILES_DIR = "inventory_files"      # below the app data folder: inventory_files/<item id>/<file>
EXPORT_HEADERS = ["Bezeichnung", "Kategorie", "Größe", "Link zum Shop", "Einzelpreis", "Anzahl",
                  "Gesamtpreis", "Parcoursplanung", "Aktiv", "Notizen"]


def _number(value, label: str, integer: bool = False):
    try:
        number = int(value) if integer else float(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{label} ist Pflicht und muss eine Zahl sein.") from None
    if number < 0:
        raise ValidationError(f"{label} darf nicht negativ sein.")
    return number


# ---------------------------------------------------------------- categories
def list_categories() -> list[InventoryCategory]:
    with session_scope() as s:
        return list(s.scalars(select(InventoryCategory)
                              .order_by(InventoryCategory.sort_order, InventoryCategory.name)))


def count_items_in_category(category_id: int) -> int:
    with session_scope() as s:
        return s.scalar(select(func.count(InventoryItem.id))
                        .where(InventoryItem.category_id == category_id))


def save_category(name: str, category_id: int | None = None) -> InventoryCategory:
    name = (name or "").strip()
    if not name:
        raise ValidationError("Der Name der Kategorie darf nicht leer sein.")
    with session_scope() as s:
        duplicate = s.scalar(select(InventoryCategory.id).where(
            func.lower(InventoryCategory.name) == name.lower(),
            InventoryCategory.id != (category_id or 0)))
        if duplicate:
            raise ValidationError(f"Die Kategorie „{name}“ gibt es schon.")
        if category_id is None:
            category = InventoryCategory(name=name)
            s.add(category)
        else:
            category = s.get(InventoryCategory, category_id)
            if category is None:
                raise ValidationError("Kategorie nicht gefunden.")
            category.name = name
        s.flush()
        return category


def delete_category(category_id: int, move_to: int | None = None) -> None:
    """Refuses while items use the category, unless they are moved to `move_to`."""
    with session_scope() as s:
        count = s.scalar(select(func.count(InventoryItem.id))
                         .where(InventoryItem.category_id == category_id))
        if count and move_to is None:
            raise ValidationError(f"Die Kategorie wird noch von {count} Artikel(n) verwendet.")
        if count:
            for item in s.scalars(select(InventoryItem)
                                  .where(InventoryItem.category_id == category_id)):
                item.category_id = move_to
        category = s.get(InventoryCategory, category_id)
        if category:
            s.delete(category)


# ---------------------------------------------------------------- items
def list_items(category_id: int | None = None, course_only: bool = False,
               active_only: bool = False) -> list[InventoryItem]:
    """`course_only` (items offered in the course plan) always implies active items."""
    with session_scope() as s:
        q = select(InventoryItem).options(selectinload(InventoryItem.category))
        if category_id is not None:
            q = q.where(InventoryItem.category_id == category_id)
        if course_only:
            q = q.where(InventoryItem.use_in_course.is_(True))
        if active_only or course_only:
            q = q.where(InventoryItem.active.is_(True))
        return list(s.scalars(q.order_by(InventoryItem.name)))


def item_total(item: InventoryItem) -> float:
    return round(item.unit_price * item.quantity, 2)


def inventory_total_value() -> float:
    """Inactive items do not count."""
    with session_scope() as s:
        return round(s.scalar(select(func.coalesce(
            func.sum(InventoryItem.unit_price * InventoryItem.quantity), 0))
            .where(InventoryItem.active.is_(True))), 2)


def set_item_active(item_id: int, active: bool) -> None:
    with session_scope() as s:
        s.get(InventoryItem, item_id).active = active


def save_item(data: dict, item_id: int | None = None) -> InventoryItem:
    name = (data.get("name") or "").strip()
    if not name:
        raise ValidationError("Bezeichnung darf nicht leer sein.")
    values = {
        "name": name,
        "category_id": data.get("category_id") or None,
        "size": (data.get("size") or "").strip() or None,
        "shop_url": (data.get("shop_url") or "").strip() or None,
        "unit_price": _number(data.get("unit_price"), "Einzelpreis"),
        "quantity": _number(data.get("quantity", 1), "Anzahl", integer=True),
        "use_in_course": bool(data.get("use_in_course")),
        "active": bool(data.get("active", True)),
        "notes": (data.get("notes") or "").strip() or None,
    }
    with session_scope() as s:
        if item_id:
            item = s.get(InventoryItem, item_id)
            if item is None:
                raise ValidationError("Eintrag nicht gefunden.")
        else:
            item = InventoryItem()
            s.add(item)
        for key, value in values.items():
            setattr(item, key, value)
        s.flush()
        return item


def delete_item(item_id: int) -> None:
    with session_scope() as s:
        item = s.get(InventoryItem, item_id)
        if item:
            s.delete(item)
    shutil.rmtree(config.APP_DATA_DIR / FILES_DIR / str(item_id), ignore_errors=True)


def export_rows(items: list[InventoryItem]) -> list[list]:
    return [[i.name, i.category.name if i.category else "", i.size or "", i.shop_url or "",
             i.unit_price, i.quantity, item_total(i), "Ja" if i.use_in_course else "Nein",
             "Ja" if i.active else "Nein", i.notes or ""] for i in items]


def import_items(records: list[dict], strategy: str) -> dict:
    """strategy: 'skip' | 'update' | 'new'. Unknown categories are created."""
    result = {"created": 0, "updated": 0, "skipped": 0}
    with session_scope() as s:
        categories = {c.name.lower(): c for c in s.scalars(select(InventoryCategory))}
        for rec in records:
            name = (rec.get("name") or "").strip()
            if not name:
                continue
            existing = (None if strategy == "new"
                        else s.scalar(select(InventoryItem).where(InventoryItem.name == name)))
            if existing is not None and strategy != "update":
                result["skipped"] += 1
                continue
            category_name = (rec.get("category") or "").strip()
            if category_name and category_name.lower() not in categories:
                categories[category_name.lower()] = InventoryCategory(name=category_name)
                s.add(categories[category_name.lower()])
            item = existing or InventoryItem(name=name)
            values = {"category": categories.get(category_name.lower()),
                      "size": rec.get("size"), "shop_url": rec.get("shop_url"),
                      "unit_price": rec.get("unit_price"), "quantity": rec.get("quantity"),
                      "use_in_course": rec.get("use_in_course"), "active": rec.get("active"),
                      "notes": rec.get("notes")}
            for key, value in values.items():     # update keeps what the file leaves empty
                if value is not None or existing is None:
                    setattr(item, key, value)
            if existing is None:
                item.unit_price = item.unit_price or 0
                item.quantity = 1 if item.quantity is None else item.quantity
                item.use_in_course = bool(item.use_in_course)
                item.active = True if item.active is None else bool(item.active)
                s.add(item)
                result["created"] += 1
            else:
                result["updated"] += 1
    return result


# ---------------------------------------------------------------- files
def list_inventory_files(item_id: int) -> list[InventoryFile]:
    with session_scope() as s:
        return s.scalars(select(InventoryFile).where(InventoryFile.item_id == item_id)
                         .order_by(InventoryFile.id)).all()


def inventory_file_path(stored: InventoryFile) -> Path:
    return config.APP_DATA_DIR / stored.stored_path


def add_inventory_file(item_id: int, source) -> InventoryFile:
    """Copy a file into the app data folder and attach it to the item."""
    source = Path(source)
    if not source.is_file():
        raise ValidationError(f"Datei '{source.name}' wurde nicht gefunden.")
    safe_name = re.sub(r"[^\w.\- ]+", "_", source.name).strip() or "datei"
    stored_path = f"{FILES_DIR}/{item_id}/{uuid.uuid4().hex[:8]}_{safe_name}"
    with session_scope() as s:
        if s.get(InventoryItem, item_id) is None:
            raise ValidationError("Eintrag nicht gefunden.")
        target = config.APP_DATA_DIR / stored_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        stored = InventoryFile(item_id=item_id, filename=source.name, stored_path=stored_path,
                               size_bytes=target.stat().st_size)
        s.add(stored)
        s.flush()
        return stored


def remove_inventory_file(file_id: int) -> None:
    with session_scope() as s:
        stored = s.get(InventoryFile, file_id)
        path = inventory_file_path(stored)
        s.delete(stored)
    path.unlink(missing_ok=True)


# ---------------------------------------------------------------- repairs
def list_repairs(item_id: int) -> list[InventoryRepair]:
    with session_scope() as s:
        return s.scalars(select(InventoryRepair).where(InventoryRepair.item_id == item_id)
                         .options(selectinload(InventoryRepair.invoice_file))
                         .order_by(InventoryRepair.date, InventoryRepair.id)).all()


def invoice_hints(item_id: int) -> dict[int, str]:
    """File id -> tooltip text for documents that are the invoice of a maintenance entry."""
    return {r.invoice_file_id: f"Rechnung zur Instandhaltung vom {r.date:%d.%m.%Y}"
            for r in list_repairs(item_id) if r.invoice_file_id}


def save_repair(data: dict, repair_id: int | None = None,
                item_id: int | None = None) -> InventoryRepair:
    """`item_id` is required for new repairs."""
    if not isinstance(data.get("date"), date):
        raise ValidationError("Das Datum der Instandhaltung ist Pflicht.")
    if _number(data.get("cost"), "Instandhaltungskosten") <= 0:
        raise ValidationError("Instandhaltungskosten müssen größer als 0 sein.")
    values = {
        "date": data["date"],
        "description": (data.get("description") or "").strip() or None,
        "cost": _number(data.get("cost"), "Instandhaltungskosten"),
        "performed_by": (data.get("performed_by") or "").strip() or None,
        "invoice_file_id": data.get("invoice_file_id") or None,
    }
    with session_scope() as s:
        if repair_id:
            repair = s.get(InventoryRepair, repair_id)
            if repair is None:
                raise ValidationError("Instandhaltung nicht gefunden.")
        else:
            repair = InventoryRepair(item_id=item_id)
        if values["invoice_file_id"]:
            invoice = s.get(InventoryFile, values["invoice_file_id"])
            if invoice is None or invoice.item_id != repair.item_id:
                raise ValidationError("Die Rechnung gehört nicht zu diesem Artikel.")
        if not repair_id:
            s.add(repair)
        for key, value in values.items():
            setattr(repair, key, value)
        s.flush()
        return repair


def delete_repair(repair_id: int) -> None:
    with session_scope() as s:
        repair = s.get(InventoryRepair, repair_id)
        if repair:
            s.delete(repair)
