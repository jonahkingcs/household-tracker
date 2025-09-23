"""
Dev script: add a sample purchase record for an existing item.

Assumes:
- At least one user already exists (added via add_test_user.py).
- At least one item already exists (added via add_test_items.py).

Run with:
    python -m src.dev.add_test_purchase
"""

import datetime as dt
import random

from src.db import models
from src.db.session import SessionLocal


def main():
    with SessionLocal() as session:
        # Pick the first user and first item in the DB
        user = session.query(models.User).first()
        item = session.query(models.Item).first()

        if not user or not item:
            print("❌ Need at least one user and one item in the database.")
            return

        # Create a purchase record
        purchase = models.PurchaseRecord(
            item_id=item.id,
            user_id=user.id,
            date_purchased=dt.datetime.utcnow(),
            quantity=random.randint(1, 3),
            total_price_cents=random.randint(150, 600),  # £1.50 – £6.00
            comments="Bought at Tesco (test data)",
        )

        session.add(purchase)
        session.commit()

        print(f"✅ Added purchase: {user.name} bought {purchase.quantity} x {item.name}")


if __name__ == "__main__":
    main()
