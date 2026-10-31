# -*- coding: utf-8 -*-
"""Auslosung: assign participants to start groups and optionally assign start targets."""
import random
import string

from bowtally.database.engine import session_scope
from bowtally.database.models import TournamentParticipant
from bowtally.services.tournament_service import get_tournament, is_active_participant


def draw_groups(tournament_id: int, group_size: int,
                rotation: str = "sequential",
                class_separated: bool = False) -> int:
    """Assign start groups to all active participants.

    rotation: 'sequential' = group A starts at target 1, B at 2 etc.
              'random' = random start target per group
    Returns the number of participants assigned.
    """
    t = get_tournament(tournament_id)
    participants = [p for p in t.participants if is_active_participant(p)]

    if class_separated:
        # group by bow_class, assign within each class
        by_class: dict = {}
        for p in participants:
            key = p.bow_class_id or 0
            by_class.setdefault(key, []).append(p)
        chunks: list[list] = []
        for plist in by_class.values():
            random.shuffle(plist)
            chunks.extend(_chunked(plist, group_size))
    else:
        shuffled = participants[:]
        random.shuffle(shuffled)
        chunks = _chunked(shuffled, group_size)

    num_targets = t.num_targets or len(chunks)
    group_labels = _group_labels(len(chunks))

    with session_scope() as s:
        # clear existing assignments first
        for p in t.participants:
            db_p = s.get(TournamentParticipant, p.id)
            if db_p:
                db_p.start_group = None
                db_p.start_number = None

        start_number = 1
        for i, chunk in enumerate(chunks):
            label = group_labels[i]
            if rotation == "random":
                start_target = random.randint(1, max(num_targets, 1))
            else:
                start_target = (i % num_targets) + 1

            for j, p in enumerate(chunk):
                db_p = s.get(TournamentParticipant, p.id)
                if db_p:
                    db_p.start_group = label
                    db_p.start_number = start_number
                    # store start target as start_time field (repurposed for draw)
                    db_p.start_time = str(start_target)
                start_number += 1

    return len(participants)


def _chunked(lst: list, size: int) -> list[list]:
    return [lst[i:i + size] for i in range(0, len(lst), size)] if lst else []


def _group_labels(n: int) -> list[str]:
    """A, B, C, …, Z, AA, AB, … for up to n groups."""
    labels = []
    for i in range(n):
        if i < 26:
            labels.append(string.ascii_uppercase[i])
        else:
            labels.append(string.ascii_uppercase[i // 26 - 1] + string.ascii_uppercase[i % 26])
    return labels
