from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.services.paths import db_path

engine = create_engine(f"sqlite:///{db_path()}", future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
