"""
Path utilities for Household Tracker.

This module centralises all filesystem paths used by the application, so that
any future changes to storage location only need to be updated here.

On macOS:
- Application data is stored under ~/Library/Application Support/HouseholdTracker
- The SQLite database is created as household.db inside that directory
"""

from pathlib import Path


def app_support_dir() -> Path:
    """
    Return the application support directory for Household Tracker.

    - On macOS, this resolves to:
      ~/Library/Application Support/HouseholdTracker
    - Creates the directory (and parents) on first call if it does not exist.

    Returns:
        Path: Filesystem path to the HouseholdTracker support directory.
    """
    base = Path.home() / "Library" / "Application Support" / "HouseholdTracker"
    base.mkdir(parents=True, exist_ok=True)  # Ensure directory exists
    return base


def db_path() -> str:
    """
    Return the absolute path to the SQLite database file.

    The database is stored as 'household.db' inside the application
    support directory.

    Returns:
        str: String path to the database file, suitable for SQLAlchemy.
    """
    return str(app_support_dir() / "household.db")
