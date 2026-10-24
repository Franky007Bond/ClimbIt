from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.trip_capability import TripCapabilityRecord


def create_trip_capability(
    session: Session,
    capability_id: uuid.UUID,
    *,
    created_at: datetime,
) -> TripCapabilityRecord:
    record = TripCapabilityRecord(
        id=capability_id,
        created_at=created_at,
        invalidated_at=None,
    )
    session.add(record)
    session.flush()
    return record


def get_trip_capability(
    session: Session,
    capability_id: uuid.UUID,
) -> TripCapabilityRecord | None:
    return session.get(TripCapabilityRecord, capability_id)


def invalidate_trip_capability(
    session: Session,
    capability_id: uuid.UUID,
    invalidated_at: datetime,
) -> None:
    record = session.get(TripCapabilityRecord, capability_id)
    if record is None:
        return
    record.invalidated_at = invalidated_at
    session.flush()


def count_active_trip_capabilities(session: Session) -> int:
    statement = (
        select(func.count())
        .select_from(TripCapabilityRecord)
        .where(TripCapabilityRecord.invalidated_at.is_(None))
    )
    return int(session.scalar(statement) or 0)
