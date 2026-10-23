from __future__ import annotations

import os
from datetime import datetime
from datetime import timedelta
from datetime import timezone


def trip_inactivity_days() -> int:
    raw = os.environ.get("TRIP_INACTIVITY_DAYS", "90").strip()
    try:
        value = int(raw)
    except ValueError:
        value = 90
    return max(1, value)


def trip_expired(last_activity_at: datetime, *, now: datetime) -> bool:
    cutoff = now - timedelta(days=trip_inactivity_days())
    return last_activity_at < cutoff
