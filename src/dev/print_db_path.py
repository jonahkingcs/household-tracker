"""
Path utilities for Household Tracker.

This module centralises all filesystem paths used by the application, so that
any future changes to storage location only need to be updated here.

On macOS:
- Application data is stored under ~/Library/Application Support/HouseholdTracker
- The SQLite database is created as household.db inside that directory
"""

from pathlib import Path

from src.services.paths import db_path

p = Path(db_path())
print("DB path:", p)
print("Exists:", p.exists())
if p.exists():
    print("Size (bytes):", p.stat().st_size)
