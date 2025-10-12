"""
SQLAlchemy ORM models for Household Tracker.

Defines the database schema:
- User:     A person in the household (for chores and purchases).
- Chore:    A recurring household task with an assigned frequency and rotation.
- ChoreCompletion: A record of when a chore was completed and by whom.

All tables use UUID hex strings as primary keys to avoid collisions.
"""

# Stdlib
import datetime as dt
import uuid

# Third-party
from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def new_id() -> str:
    """Generate a new UUID hex string for use as a primary key."""
    return uuid.uuid4().hex


class Base(DeclarativeBase):
    """Declarative base class for all ORM models."""
    pass

# ---------------------------
# Users
# ---------------------------

class User(Base):
    """Household user who participates in chores and purchases."""
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=new_id
        ) # Unique ID
    name: Mapped[str] = mapped_column(
        String, nullable=False
        ) # Display name of the user
    avatar_path: Mapped[str | None] = mapped_column(
        String, nullable=True
        ) # Optional path to profile image
    active: Mapped[int] = mapped_column(
        Integer, default=1
        ) # 1 = active in rotations, 0 = removed
    
# ---------------------------
# Chores: Chores & Completion Records
# ---------------------------

class Chore(Base):
    """A recurring household chore (e.g., 'Vacuum', 'Take out trash')."""
    __tablename__ = "chores"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=new_id
        ) # Unique ID
    name: Mapped[str] = mapped_column(
        String, nullable=False
        ) # Short name of the chore
    description: Mapped[str] = mapped_column(
        String, default=""
        ) # Optional details about the chore
    frequency_days: Mapped[int] = mapped_column(
        Integer, default=7
        ) # How often the chore should repeat
    next_due_date: Mapped[dt.datetime | None] = mapped_column(
        DateTime, nullable=True
        ) # When the chore is next due
    next_assignee_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("users.id")
        ) # Who is next in rotation
    next_assignee = relationship(
        "User", foreign_keys=[next_assignee_id]
        ) # Link to User model


class ChoreCompletion(Base):
    """A record of a completed chore with metadata (who, when, duration, etc.)."""
    __tablename__ = "chore_completions"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=new_id
        ) # Unique ID
    chore_id: Mapped[str] = mapped_column(
        String, ForeignKey("chores.id")
        ) # Which chore was completed
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id")
        ) # Who did the chore
    date_completed: Mapped[dt.datetime] = mapped_column(
        DateTime, default=dt.datetime.utcnow
        ) # Timestamp of completion
    duration_minutes: Mapped[int] = mapped_column(
        Integer, default=0
        ) # How long it took
    comments: Mapped[str] = mapped_column(
        String, default=""
        ) # Optional free-text notes or anecdotes
    was_late: Mapped[int] = mapped_column(
        Integer, default=0
        ) # 1 if chore was overdue at completion
    backdated: Mapped[int] = mapped_column(
        Integer, default=0
        ) # 1 if completion was logged after the fact
    chore = relationship("Chore")   # ORM navigation to parent chore; enables joinedload()
    user  = relationship("User")    # ORM navigation to actor; may be None if user was deleted

# ---------------------------
# Purchases: Items & Records
# ---------------------------

class Item(Base):
    """
    A recurring household item that needs to be restocked (e.g., 'Toilet Paper', 'Milk').

    Mirrors `Chore`:
    - `frequency_days` controls how often it should be restocked.
    - `next_restock_date` is the next due date.
    - `next_buyer_id` points to the user next in the purchase rotation.
    """
    __tablename__ = "items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(
        String, nullable=False
    )  # Short name of the item
    description: Mapped[str] = mapped_column(
        String, default=""
    )  # Optional details about the item (brand prefs, sizes, etc.)
    frequency_days: Mapped[int] = mapped_column(
        Integer, default=7
    )  # How often the item should be restocked
    next_restock_date: Mapped[dt.datetime | None] = mapped_column(
        DateTime, nullable=True
    )  # When the item is next due to be purchased
    next_buyer_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("users.id")
    )  # Who is next in rotation to buy
    next_buyer = relationship(
        "User", foreign_keys=[next_buyer_id]
    )  # Link to User model


class PurchaseRecord(Base):
    """
    A record of a purchase for an `Item`.

    Mirrors `ChoreCompletion`:
    - Tracks who bought it, when, quantity, and total price.
    - `was_late` / `backdated` keep parity with chores for analytics and fairness.
    """
    __tablename__ = "purchase_records"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    item_id: Mapped[str] = mapped_column(
        String, ForeignKey("items.id")
    )  # Which item was purchased
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id")
    )  # Who bought the item
    date_purchased: Mapped[dt.datetime] = mapped_column(
        DateTime, default=dt.datetime.utcnow
    )  # Timestamp of purchase

    # Core purchase metadata
    quantity: Mapped[int] = mapped_column(
        Integer, default=1
    )  # Units purchased (e.g., 1 pack, 2 bottles)
    total_price_cents: Mapped[int] = mapped_column(
        Integer, default=0
    )  # Total cost in minor units (pennies/cents) to avoid float issues
    comments: Mapped[str] = mapped_column(
        String, default=""
    )  # Optional notes (brand, store, etc.)

    # Parity flags with chores for consistent analytics
    was_late: Mapped[int] = mapped_column(
        Integer, default=0
    )  # 1 if purchase was overdue at time of logging
    backdated: Mapped[int] = mapped_column(
        Integer, default=0
    )  # 1 if logged after the fact

    item = relationship("Item")     # ORM navigation to purchased item; enables joinedload()
    user = relationship("User")     # ORM navigation to buyer; may be None if user was deleted