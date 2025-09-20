"""
Log a single test completion for an existing chore and advance rotation/due date.

Run:
    source venv/bin/activate
    python -m src.dev.add_test_completion
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import Base, Chore, ChoreCompletion, User
from src.db.session import SessionLocal, engine


def _active_users(sess: Session) -> list[User]:
    return list(sess.scalars(select(User).where(User.active == 1).order_by(User.name)))


def _advance_rotation(sess: Session, chore: Chore) -> None:
    """Advance next_assignee_id to the next active user (by name order)."""
    users = _active_users(sess)
    if not users:
        chore.next_assignee_id = None
        return
    ids = [u.id for u in users]
    if not chore.next_assignee_id or chore.next_assignee_id not in ids:
        chore.next_assignee_id = ids[0]
        return
    idx = ids.index(chore.next_assignee_id)
    chore.next_assignee_id = ids[(idx + 1) % len(ids)]


def main() -> None:
    # Ensure schema exists
    Base.metadata.create_all(bind=engine)

    sess: Session = SessionLocal()
    try:
        # Pick the first chore (or change this to pick by name)
        chore = sess.scalars(select(Chore).order_by(Chore.name)).first()
        if not chore:
            print("⚠️ No chores found. Run: python -m src.dev.add_test_chores")
            return

        # Choose the current next assignee; if missing, pick the first active user
        user = None
        if chore.next_assignee_id:
            user = sess.get(User, chore.next_assignee_id)
        if not user:
            user = sess.scalars(
                select(User).where(User.active == 1).order_by(User.name)
            ).first()
        if not user:
            print("⚠️ No active users found. Add a user first.")
            return

        # Log a completion
        now = dt.datetime.utcnow()
        completion = ChoreCompletion(
            chore_id=chore.id,
            user_id=user.id,
            date_completed=now,
            duration_minutes=12,
            comments="Test completion via dev script",
            was_late=0,
            backdated=0,
        )
        sess.add(completion)

        # Advance rotation and bump due date by frequency
        _advance_rotation(sess, chore)
        chore.next_due_date = now + dt.timedelta(days=chore.frequency_days)

        sess.commit()
        print(
            f"✅ Logged completion for '{chore.name}' by {user.name}. "
            f"Next due: {chore.next_due_date.date()}"
        )
    finally:
        sess.close()


if __name__ == "__main__":
    main()
