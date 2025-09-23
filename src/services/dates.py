"""
dates.py — small date/time helpers for UI and scheduling.
"""
from __future__ import annotations

from datetime import datetime, timedelta


def humanize_due(dt: datetime | None, *, now: datetime | None = None) -> str:
    """Return 'Today', 'Tomorrow', 'in 3d', or 'Overdue by 2d' for a due datetime."""
    if dt is None:
        return "—"
    now = now or datetime.now()
    d_days = (dt.date() - now.date()).days
    if d_days == 0:
        return "Today"
    if d_days == 1:
        return "Tomorrow"
    if d_days > 1:
        return f"in {d_days}d"
    # overdue
    late = abs(d_days)
    return f"Overdue by {late}d"

def bump_due(base: datetime, freq_days: int) -> datetime:
    """Next due = base + frequency (days)."""
    return base + timedelta(days=max(1, int(freq_days)))
