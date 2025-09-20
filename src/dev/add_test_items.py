"""
Dev script: seed the database with a few test household items.

Run with:
    python -m src.dev.add_test_items
"""

from src.db.session import SessionLocal
from src.db import models


def main():
    with SessionLocal() as session:
        # Example items to seed
        items = [
            models.Item(name="Milk", description="Semi-skimmed 2L", frequency_days=3),
            models.Item(name="Toilet Paper", description="9-pack", frequency_days=7),
            models.Item(name="Dish Soap", description="Fairy Liquid", frequency_days=14),
        ]

        session.add_all(items)
        session.commit()

        print("✅ Added test items:", [item.name for item in items])


if __name__ == "__main__":
    main()
