"""
rotation.py — minimal rotation utilities.
For now: global rotation = all active users ordered by name.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import User


def _active_user_ids_sorted(s: Session) -> list[str]:
    return list(s.scalars(select(User.id).where(User.active == 1).order_by(User.name.asc())))

def next_user_id(s: Session, current_user_id: str | None) -> str | None:
    """
    Given the current next user (or None), return the next active user in cycle.
    If no active users: return None.
    """
    ids = _active_user_ids_sorted(s)
    if not ids:
        return None
    if current_user_id is None or current_user_id not in ids:
        return ids[0]
    i = ids.index(current_user_id)
    return ids[(i + 1) % len(ids)]
