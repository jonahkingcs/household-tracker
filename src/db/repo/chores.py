"""
chores.py — Repository helpers for chores & completions.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, joinedload

from src.db.models import Chore, ChoreCompletion
from src.services import rotation
from src.services.dates import bump_due

# --------- Queries ---------

def list_chores(session: Session, order_by_due: bool = True) -> list[Chore]:
    """
    Return all non-deleted chores ordered by next due (then name).
    joinedload next_assignee so UI can show the name without extra queries.
    """
    stmt = select(Chore).options(joinedload(Chore.next_assignee))
    if order_by_due:
        stmt = stmt.order_by(Chore.next_due_date.asc().nulls_last(), Chore.name.asc())
    else:
        stmt = stmt.order_by(Chore.name.asc())
    return list(session.scalars(stmt))

def get_chore(session: Session, chore_id: str) -> Chore | None:
    return session.get(Chore, chore_id)

# --------- CRUD ---------

def create_chore(
    session: Session,
    name: str,
    description: str,
    frequency_days: int,
    assignee_id: str | None = None,
) -> Chore:
    """Create a chore; if assignee unset, pick first active user; next due = today + freq."""
    if assignee_id is None:
        assignee_id = rotation.next_user_id(session, None)
    now = datetime.now()
    c = Chore(
        name=name.strip(),
        description=description or "",
        frequency_days=int(frequency_days),
        next_due_date=bump_due(now, int(frequency_days)),
        next_assignee_id=assignee_id,
    )
    session.add(c)
    session.commit()
    session.refresh(c)
    return c

def update_chore(
    session: Session,
    chore_id: str,
    *,
    name: str | None = None,
    description: str | None = None,
    frequency_days: int | None = None,
    next_assignee_id: str | None = None,
    next_due_date: datetime | None = None,
) -> Chore:
    """Update fields on a chore and commit."""
    c = get_chore(session, chore_id)
    if not c:
        raise ValueError("Chore not found")
    if name is not None:
        c.name = name.strip()
    if description is not None:
        c.description = description
    if frequency_days is not None:
        c.frequency_days = int(frequency_days)
    if next_assignee_id is not None:
        c.next_assignee_id = next_assignee_id
    if next_due_date is not None:
        c.next_due_date = next_due_date
    session.commit()
    session.refresh(c)
    return c

def delete_chore(session: Session, chore_id: str) -> None:
    """
    Delete a chore and its completion rows.
    (History preservation can be added later via soft-delete if you prefer.)
    """
    session.execute(delete(ChoreCompletion).where(ChoreCompletion.chore_id == chore_id))
    c = get_chore(session, chore_id)
    if c:
        session.delete(c)
    session.commit()

# --------- Actions ---------

def complete_chore(
    session: Session,
    chore_id: str,
    who_user_id: str,
    duration_minutes: int,
    comments: str = "",
    when: datetime | None = None,
) -> ChoreCompletion:
    """
    Log completion, advance rotation, bump next due.
    Returns the created ChoreCompletion row.
    """
    c = get_chore(session, chore_id)
    if not c:
        raise ValueError("Chore not found")
    when = when or datetime.now()

    was_late = int(c.next_due_date is not None and when.date() > c.next_due_date.date())
    comp = ChoreCompletion(
        chore_id=chore_id,
        user_id=who_user_id,
        date_completed=when,
        duration_minutes=max(0, int(duration_minutes)),
        comments=comments or "",
        was_late=was_late,
        backdated=0,
    )
    session.add(comp)

    # Advance rotation and bump due
    c.next_assignee_id = rotation.next_user_id(session, c.next_assignee_id)
    c.next_due_date = bump_due(when, c.frequency_days)

    session.commit()
    session.refresh(comp)
    return comp
