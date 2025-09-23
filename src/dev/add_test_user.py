"""
Seed the database with a single test user.
Run from project root:
    source venv/bin/activate
    python -m src.dev.add_test_user
"""

# Third-party
from sqlalchemy.orm import Session

# First-party
from src.db.models import Base, User
from src.db.session import SessionLocal, engine


def main() -> None:
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    sess: Session = SessionLocal()
    try:
        # Add a user to test with
        user = User(name="Joe", active=True)
        sess.add(user)
        sess.commit()
        print(f"✅ Added user: id={user.id}  name={user.name}")
    finally:
        sess.close()

if __name__ == "__main__":
    main()
