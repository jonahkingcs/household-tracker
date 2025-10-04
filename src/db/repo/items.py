"""
items.py — Repository helpers for items & purchases.

Overview
--------
- Query helpers for listing and fetching `Item` rows (with next buyer eager-loaded).
- CRUD helpers for `Item`.
- Action helper for logging a `PurchaseRecord` that also advances rotation and bumps
  the next restock date.

Notes
-----
- Mirrors the structure and conventions used in chores.py.
- Uses `rotation.next_user_id(...)` to pick the next buyer (alphabetical among active users).
- Timestamps default to `datetime.now()`; pass `when=` to backdate a purchase.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from src.db.models import Item, PurchaseRecord
from src.services import rotation
from src.services.dates import bump_due

# --------- Queries ---------

def list_items(session: Session, order_by_due: bool = True) -> list[Item]:
    """
    Return all items ordered by next restock (then name).

    Eager-loads `next_buyer` so the UI can show the assignee name
    without N+1 queries.

    Args:
        session: Active SQLAlchemy session.
        order_by_due: If True, order by Item.next_restock_date ASC with NULLS last,
                      then Item.name; otherwise order by Item.name.

    Returns:
        List[Item]: materialized ORM rows.
    """
    stmt = select(Item).options(joinedload(Item.next_buyer))
    if order_by_due:
        stmt = stmt.order_by(Item.next_restock_date.asc().nulls_last(), Item.name.asc())
    else:
        stmt = stmt.order_by(Item.name.asc())
    return list(session.scalars(stmt))


def get_item(session: Session, item_id: str) -> Item | None:
    """Fetch a single item by id (or None if missing)."""
    return session.get(Item, item_id)


# --------- CRUD ---------

def create_item(
    session: Session,
    *,
    name: str,
    description: str,
    frequency_days: int,
    first_buyer_id: str | None = None,
) -> Item:
    """
    Create and persist a new item.

    If `first_buyer_id` is not provided, we pick the first active user using
    the same rotation helper as chores. `next_restock_date` is initialized to
    today + `frequency_days`.

    Returns:
        The newly created Item (refreshed from DB).
    """
    if first_buyer_id is None:
        first_buyer_id = rotation.next_user_id(session, None)
    now = datetime.now()
    it = Item(
        name=name.strip(),
        description=description or "",
        frequency_days=int(frequency_days),
        next_restock_date=bump_due(now, int(frequency_days)),
        next_buyer_id=first_buyer_id,
    )
    session.add(it)
    session.commit()
    session.refresh(it)
    return it


def update_item(
    session: Session,
    item_id: str,
    *,
    name: str | None = None,
    description: str | None = None,
    frequency_days: int | None = None,
    next_buyer_id: str | None = None,
    next_restock_date: datetime | None = None,
) -> Item:
    """
    Patch-update fields on an item and return the updated row.

    Semantics:
      - Only parameters that are not None are applied.
      - Passing `next_buyer_id=None` leaves it unchanged (matches chores.py style).

    Raises:
      ValueError: if the item does not exist.
    """
    it = get_item(session, item_id)
    if not it:
        raise ValueError("Item not found")

    if name is not None:
        it.name = name.strip()
    if description is not None:
        it.description = description
    if frequency_days is not None:
        it.frequency_days = int(frequency_days)
    if next_buyer_id is not None:
        it.next_buyer_id = next_buyer_id
    if next_restock_date is not None:
        it.next_restock_date = next_restock_date

    session.commit()
    session.refresh(it)
    return it


def delete_item(session: Session, item_id: str) -> None:
    """
    Delete an item. Purchase history (`PurchaseRecord`) is preserved.

    No error is raised if the item is already missing.
    """
    it = get_item(session, item_id)
    if it:
        session.delete(it)
        session.commit()


# --------- Actions ---------

def log_purchase(
    session: Session,
    *,
    item_id: str,
    user_id: str,
    quantity: int,
    total_price_cents: int,
    comments: str = "",
    when: datetime | None = None,
) -> PurchaseRecord:
    """
    Log a purchase, advance rotation, and bump the next restock date.

    Side effects:
      - Inserts a `PurchaseRecord` with flags:
          * was_late = 1 if purchase date > current next_restock_date (date-based).
          * backdated = 1 if a custom `when` is provided; else 0.
      - Updates parent Item:
          * next_buyer_id moves to the next active user (via rotation helper).
          * next_restock_date = `bump_due(when_or_now, frequency_days)`.

    Returns:
      The persisted PurchaseRecord.
    """
    it = get_item(session, item_id)
    if not it:
        raise ValueError("Item not found")

    when = when or datetime.now()

    # Compute lateness using date precision (consistent with chores).
    was_late = int(it.next_restock_date is not None and when.date() > it.next_restock_date.date())
    rec = PurchaseRecord(
        item_id=item_id,
        user_id=user_id,
        date_purchased=when,
        quantity=max(1, int(quantity)),
        total_price_cents=max(0, int(total_price_cents)),
        comments=(comments or "").strip(),
        was_late=was_late,
        backdated=0 if when is None else 1,
    )
    session.add(rec)

    # Advance rotation and bump next restock.
    # (Mirror chores.py: move to next user after the *current* next_buyer.)
    it.next_buyer_id = rotation.next_user_id(session, it.next_buyer_id)
    it.next_restock_date = bump_due(when, it.frequency_days)

    session.commit()
    session.refresh(rec)
    return rec