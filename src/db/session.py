"""
Database session setup for Household Tracker.

This module configures the SQLAlchemy engine and session factory.
All database access in the application should go through SessionLocal
to ensure consistent connection handling.

- Uses SQLite for local, offline storage.
- Database file path is resolved by src.services.paths.db_path().
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.services.paths import db_path

# SQLAlchemy Engine
# -----------------
# The engine manages the core database connection pool.
# Here we use SQLite with a file path under the app support directory.
# `future=True` enables SQLAlchemy 2.0-style behavior.
engine = create_engine(f"sqlite:///{db_path()}", future=True)

# Session Factory
# ---------------
# SessionLocal is a factory for creating new Session objects.
# Each session manages a unit of work with the database.
# - autoflush=False: don’t automatically flush pending changes before queries
# - autocommit=False: explicit commit required for safety
# - future=True: enable 2.0-style API
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)