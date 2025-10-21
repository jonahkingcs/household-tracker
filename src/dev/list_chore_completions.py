from datetime import datetime, timedelta

from src.db.repo.chores import list_completions
from src.db.session import SessionLocal

with SessionLocal() as s:
    rows = list_completions(s, date_from=datetime.utcnow() - timedelta(days=90))
    print(len(rows), "rows")
    if rows:
        r = rows[0]
        print(r.date_completed, getattr(r.chore, "name", None), getattr(r.user, "name", None))
