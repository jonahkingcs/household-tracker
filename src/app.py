"""
Household Tracker — application entry point.

This module bootstraps the Qt application, ensures the SQLite schema exists,
loads the global stylesheet (QSS), and shows the main window.

Key responsibilities:
- Create database tables once based on SQLAlchemy models (no migrations here).
- Configure QApplication (name, fonts/theme via QSS).
- Instantiate and show the MainWindow.

Run directly:
    python -m src.app
"""

from __future__ import annotations

import sys

# Stdlib
from pathlib import Path

# Third-party
from PySide6.QtWidgets import QApplication

# First-party
from src.db.models import Base
from src.db.session import engine
from src.views.main_window import MainWindow


def load_qss(app):
    """
    Load and apply the global QSS stylesheet if present.

    Looks for `styles/rounded_dark.qss` relative to this file and, if found,
    applies it to the entire application. Missing stylesheet is a no-op.
    """
    qss_path = Path(__file__).with_name("styles") / "rounded_dark.qss"
    if qss_path.exists():
        # Use Path.read_text to avoid UP015 ("unnecessary mode argument")
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))


def main():
    """
    Application bootstrap.

    - Ensures all SQLAlchemy models have corresponding tables in SQLite.
    - Creates and configures the QApplication instance.
    - Loads the global stylesheet (if available).
    - Constructs and shows the main window.
    - Starts the Qt event loop and exits with its return code.
    """

    # 1) Ensure the database schema exists (creates tables if they do not).
    # Note: For schema changes later, will switch to Alembic migrations
    Base.metadata.create_all(bind=engine)

    # 2) Create the QApplication (must exist before any Qt widgets)
    app = QApplication(sys.argv)
    app.setApplicationName("Household Tracker")

    # 3) Build and show the main window (the rest of the app hangs off this)
    win = MainWindow()
    win.show()

    # 4) Enter the Qt event loop; return its exit code to the OS
    sys.exit(app.exec())


if __name__ == "__main__":
    # When run as a script, execute the bootstrap
    main()
