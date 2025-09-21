"""
Repository helpers for Users.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import User


def list_users(session: Session) -> list[User]:
    """Return all users ordered by name."""
    return list(session.scalars(select(User).order_by(User.name)))


def create_user(session: Session, name: str, avatar_path: str | None = None) -> User:
    """Create and persist a new active user."""
    user = User(name=name.strip(), avatar_path=avatar_path, active=1)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def set_active(session: Session, user_id: str, active: bool) -> None:
    """Set a user's active flag and commit."""
    user = session.get(User, user_id)
    if not user:
        raise ValueError("User not found")
    user.active = 1 if active else 0
    session.commit()