"""
Repository helpers for Items and PurchaseRecords.

Responsibilities
---------------
- CRUD for `Item` (recurring purchase).
- Logging `PurchaseRecord` and advancing rotation / next restock date.
- Read helpers with sensible ordering (due-first).
"""


from __future__ import annotations

import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.db.models import Item, PurchaseRecord
from src.services.dates import bump_due, safe_now
from src.services.rotation import next_active_user_after

# Sentinel to distinguish "caller did not pass a value" from "explicitly set None".
_UNSET = object()

# ---------- Items ----------

def list_items(session: Session, order_by_due: bool = True) -> list[Item]:
    """
    Return all items.

    Args:
        session: Open SQLAlchemy session.
        order_by_due: If True, order by next_restock_date, pushing NULLs last.
                      Otherwise order alphabetically by name.

    Returns:
        List of Item rows.
    """
    if order_by_due:
        # Order NULL due dates last by coalescing to a very-distant future date.
        far = dt.datetime(9999, 1, 1)
        stmt = select(Item).order_by(func.coalesce(Item.next_restock_date, far))
    else:
        stmt = select(Item).order_by(Item.name)
    return list(session.scalars(stmt))

def get_item(session: Session, item_id: str) -> Item | None:
    """Fetch a single item by id, or None if not found."""
    return session.get(Item, item_id)

def create_item(
        session: Session,
        *,
        name: str,
        description: str = "",
        frequency_days: int,
        first_buyer_id: str | None,
        initial_due: dt.datetime | None = None,
) -> Item:
    """
    Create and persist a new recurring item.

    If `initial_due` is not supplied, we set `next_restock_date = now + frequency_days`.
    If `first_buyer_id` is None, the item starts unassigned.

    Returns:
        The freshly persisted Item (refreshed from DB).
    """
    now = safe_now()
    item = Item(
        name=name.strip(),
        description=description.strip(),
        frequency_days=frequency_days,
        next_restock_date=initial_due or bump_due(now, frequency_days),
        next_buyer_id=first_buyer_id
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def update_item(
    session: Session,
    item_id: str,
    *,
    name: str | None = None,
    description: str | None = None,
    frequency_days: int | None = None,
    next_restock_date: dt.datetime | None = None,
    next_buyer_id: str | None | object = _UNSET,    # use sentinel to allow explicit None
) -> Item:
    """
    Patch-update fields on an Item and return the updated row.

    Use `next_buyer_id=_UNSET` (default) to leave it unchanged. Pass `None` to clear it.
    """
    item = session.get(Item, item_id)
    if not item:
        raise ValueError("Item not found")
    
    if name is not None:
        item.name = name.strip()
    if description is not None:
        item.description = description.strip()
    if frequency_days is not None:
        item.frequency_days = int(frequency_days)
    if next_restock_date is not None:
        item.next_restock_date = next_restock_date
    if next_buyer_id is not _UNSET:
        # Allow explicitly setting to None (unassigned).
        item.next_buyer_id = next_buyer_id  # type: ignore[assignment]

    session.commit()
    session.refresh(item)
    return item


def delete_item(session: Session, item_id: str) -> None:
    """
    Permanently delete an item.

    Purchase history (`PurchaseRecord`) is left intact.
    """
    item = session.get(Item, item_id)
    if not item:
        return
    session.delete(item)
    session.commit()


# ---------- Purchases ----------

def log_purchase(
    session: Session,
    *,
    item_id: str,
    user_id: str,
    quantity: int,
    total_price_cents: int,
    comments: str = "",
    when: dt.datetime | None = None,
) -> PurchaseRecord:
    """
    Create a PurchaseRecord and advance the item's rotation.

    Effects:
      - Inserts a new `PurchaseRecord` for (item_id, user_id).
      - Sets `was_late=1` if the purchase date is after the current due.
      - Sets `backdated=1` if `when` is provided (i.e., not "now").
      - Bumps `item.next_restock_date` by `item.frequency_days`.
      - Advances `item.next_buyer_id` to the next active user (alphabetical).

    Returns:
      The persisted PurchaseRecord.
    """
    item = session.get(Item, item_id)
    if not item:
        raise ValueError("Item not found")
    
    now = when or safe_now()

    rec = PurchaseRecord(
        item_id=item_id,
        user_id=user_id,
        date_purchased=now,
        quantity=max(1, int(quantity)),
        total_price_cents=max(0, int(total_price_cents)),
        comments=comments.strip(),
        was_late=1 if (item.next_restock_date and now > item.next_restock_date) else 0,
        backdated=1 if when is not None else 0,
    )
    session.add(rec)

    # Advance rotation and due date on the parent item.
    item.next_restock_date = bump_due(now, item.frequency_days)
    item.next_buyer_id = next_active_user_after(session, user_id)

    session.commit()
    session.refresh(rec)
    return rec