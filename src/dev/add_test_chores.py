"""
Add a couple of test chores if missing.

Run:
    source venv/bin/activate
    python -m src.dev.add_test_chores
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from src.db.models import Base, Chore, User
from src.db.session import SessionLocal, engine


def main() -> None:
    # Ensure tables exist (harmless if already created)
    Base.metadata.create_all(bind=engine)

    sess: Session = SessionLocal()
    try:
        # Ensure at least one active user exists (who will be next_assignee)
        first_user = sess.scalars(
            select(User).where(User.active == 1).order_by(User.name)
        ).first()
        if not first_user:
            print("⚠️ No active users found. Add a user first (e.g., add_test_user).")
            return

        # If there are no chores, add two simple ones
        existing_count = sess.scalar(select(func.count()).select_from(Chore))
        if existing_count == 0:
            now = dt.datetime.utcnow()
            dishes = Chore(
                name="Dishes",
                description="Wash dishes and tidy the sink",
                frequency_days=2,
                next_due_date=now + dt.timedelta(days=2),
                next_assignee_id=first_user.id,
            )
            vacuum = Chore(
                name="Vacuum",
                description="Vacuum all common areas",
                frequency_days=7,
                next_due_date=now + dt.timedelta(days=7),
                next_assignee_id=first_user.id,
            )
            sess.add_all([dishes, vacuum])
            sess.commit()
            print("✅ Added chores: Dishes, Vacuum")
        else:
            print("ℹ️ Chores already exist; nothing to add.")
    finally:
        sess.close()


if __name__ == "__main__":
    main()
