"""
Add four extra test chores if missing.

Run:
    source venv/bin/activate
    python -m src.dev.add_test_chores
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import Base, Chore, User
from src.db.session import SessionLocal, engine


def _existing_chore_names(sess: Session) -> set[str]:
    return set(sess.scalars(select(Chore.name)).all())


def _ensure_active_user(sess: Session) -> User | None:
    return sess.scalars(
        select(User).where(User.active == 1).order_by(User.name)
    ).first()


def main() -> None:
    # Ensure tables exist (harmless if already created)
    Base.metadata.create_all(bind=engine)

    sess: Session = SessionLocal()
    try:
        first_user = _ensure_active_user(sess)
        if not first_user:
            print("⚠️ No active users found. Add a user first (e.g., add_test_user).")
            return

        target_chores = [
            {
                "name": "Clean Bathroom",
                "description": "Sink, loo, shower, mirrors",
                "frequency_days": 7,
            },
            {
                "name": "Mop Floors",
                "description": "Kitchen + hallway",
                "frequency_days": 14,
            },
            {
                "name": "Take Out Rubbish",
                "description": "Kitchen bin to outside bin",
                "frequency_days": 2,
            },
            {
                "name": "Wipe Kitchen Surfaces",
                "description": "Counters, hob, handles",
                "frequency_days": 3,
            },
        ]

        existing = _existing_chore_names(sess)
        now = dt.datetime.utcnow()

        created: list[str] = []
        for cfg in target_chores:
            if cfg["name"] in existing:
                continue
            ch = Chore(
                name=cfg["name"].strip(),
                description=cfg["description"],
                frequency_days=int(cfg["frequency_days"]),
                # Next due = now + frequency (keeps things visible on the board)
                next_due_date=now + dt.timedelta(days=int(cfg["frequency_days"])),
                next_assignee_id=first_user.id,
            )
            sess.add(ch)
            created.append(cfg["name"])

        if created:
            sess.commit()
            print("✅ Added chores:", ", ".join(created))
        else:
            print("ℹ️ All target test chores already exist; nothing to add.")
    finally:
        sess.close()


if __name__ == "__main__":
    main()
