# -*- coding: utf-8 -*-
"""Old helper rows -> member rows. Shared by Alembic migration 0029 and the restore of old backups."""


def helpers_to_members(helpers: list[dict], assignments: list[dict]) -> tuple[list[dict], list[dict]]:
    """Convert rows of the old `helpers` / `tournament_helpers` tables to the member schema.

    Member ids stay the helper ids, member numbers are assigned in id order (1, 2, 3 ...).
    The same helper assigned twice to one tournament is merged into one assignment.
    """
    members = [
        {"id": h["id"], "member_number": str(number), "first_name": h["first_name"],
         "last_name": h["last_name"], "phone": h.get("phone"), "email": h.get("email"),
         "notes": h.get("notes"), "active": h.get("active", True), "is_tournament_helper": True}
        for number, h in enumerate(sorted(helpers, key=lambda h: h["id"]), start=1)
    ]
    merged: dict[tuple, dict] = {}
    for a in sorted(assignments, key=lambda a: a["id"]):
        row = {"id": a["id"], "tournament_id": a["tournament_id"], "member_id": a["helper_id"],
               "task": a.get("task"), "time_from": a.get("time_from"), "time_to": a.get("time_to"),
               "confirmed": bool(a.get("confirmed"))}
        first = merged.setdefault((row["tournament_id"], row["member_id"]), row)
        if first is not row:
            first["confirmed"] = first["confirmed"] or row["confirmed"]
            for key in ("task", "time_from", "time_to"):
                first[key] = first[key] or row[key]
    return members, list(merged.values())
