"""
users.py — Repository helpers for User entities.

This module provides a thin abstraction over SQLAlchemy queries
for the `User` model. Repository helpers are responsible for:

- Listing all users (ordered by name)
- Creating a new user
- Activating/deactivating an existing user

These functions are intentionally simple wrappers around SQLAlchemy
so that UI code (dialogs, views) does not need to know about query syntax.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import User


def list_users(session: Session) -> list[User]:
    """
    Return all users ordered by name.

    Args:
        session: SQLAlchemy Session (caller manages lifecycle).

    Returns:
        List of User ORM objects sorted alphabetically by name.
    """

    stmt = select(User).order_by(User.name)
    return list(session.scalars(stmt))


def create_user(session: Session, name: str, avatar_path: str | None = None) -> User:
    """
    Create and persist a new active user.

    Args:
        session: SQLAlchemy Session.
        name: Display name for the new user. Leading/trailing whitespace is stripped.
        avatar_path: Optional path to a profile image.

    Returns:
        The newly created User ORM object (refreshed with DB defaults).
    """
    user = User(name=name.strip(), avatar_path=avatar_path, active=1)

    # Stage object for persistence
    session.add(user)

    # Commit immediately so that 'id' and timestamps are assigned
    session.commit()

    # Refresh to populate any defaults (like UUID primary key)
    session.refresh(user)
    return user


def set_active(session: Session, user_id: str, active: bool) -> None:
    """
    Set a user's 'active' flag and persist change.

    Used to toggle whether the user is included in chore/item rotations.
    Deactivated users remain in the database for historical reporting.

    Args:
        session: SQLAlchemy Session.
        user_id: Primary key of the User to update.
        active: True to mark as active, False to deactivate.

    Raises:
        ValueError: if no User with the given ID exists.
    """
    user = session.get(User, user_id)
    if not user:
        raise ValueError("User not found")
    
    # Flip active flag (1 = active, 0 = inactive)
    user.active = 1 if active else 0
    session.commit()