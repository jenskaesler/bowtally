# -*- coding: utf-8 -*-
"""Links to announcements already published elsewhere (Ausschreibungslinks).

Pure promotion aid for the tournament dashboard: no reachability check, no link to the
announcement PDF or the phase workflow; several links per platform are allowed.
"""
from sqlalchemy import func, select

from bowtally.database.engine import session_scope
from bowtally.database.models import AnnouncementLink
from bowtally.services import ValidationError

CUSTOM = "custom"
PLATFORMS = {
    "website": "Website",
    "facebook": "Facebook",
    "instagram": "Instagram",
    "mein_bogenturnier": "Mein Bogenturnier",
    CUSTOM: "Andere …",
}


def platform_name(link) -> str:
    """Display name: the free text for "custom", else the platform's label."""
    if link.platform == CUSTOM:
        return link.platform_label or "Andere"
    return PLATFORMS.get(link.platform, link.platform)


def list_links(tournament_id: int) -> list[AnnouncementLink]:
    with session_scope() as s:
        return list(s.scalars(select(AnnouncementLink)
                              .where(AnnouncementLink.tournament_id == tournament_id)
                              .order_by(AnnouncementLink.sort_order, AnnouncementLink.id)))


def save_link(data: dict, link_id: int | None, tournament_id: int) -> AnnouncementLink:
    platform = data.get("platform") or ""
    label = (data.get("platform_label") or "").strip()
    url = (data.get("url") or "").strip()
    if platform not in PLATFORMS:
        raise ValidationError("Bitte eine Plattform wählen.")
    if platform == CUSTOM and not label:
        raise ValidationError("Bitte den Namen der Plattform eingeben.")
    if not url:
        raise ValidationError("Bitte die URL eingeben.")
    with session_scope() as s:
        if link_id:
            link = s.get(AnnouncementLink, link_id)
        else:
            last = s.scalar(select(func.max(AnnouncementLink.sort_order))
                            .where(AnnouncementLink.tournament_id == tournament_id))
            link = AnnouncementLink(tournament_id=tournament_id, sort_order=(last or 0) + 1)
            s.add(link)
        link.platform = platform
        link.platform_label = label if platform == CUSTOM else None
        link.url = url
        s.flush()
        return link


def delete_link(link_id: int) -> None:
    """Hard delete (no history needed)."""
    with session_scope() as s:
        link = s.get(AnnouncementLink, link_id)
        if link is not None:
            s.delete(link)
