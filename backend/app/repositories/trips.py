from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.trip import TripPlanRunRecord
from app.models.trip import TripRecord
from app.models.trip import TripShareLinkRecord
from app.trip_expiry import trip_expired


def create_trip(
    session: Session,
    *,
    trip_id: uuid.UUID,
    capability_id: uuid.UUID,
    route_id: uuid.UUID,
    plan_run_id: uuid.UUID,
    created_at: datetime,
) -> TripRecord:
    record = TripRecord(
        id=trip_id,
        capability_id=capability_id,
        route_id=route_id,
        latest_plan_run_id=plan_run_id,
        created_at=created_at,
        last_activity_at=created_at,
        deleted_at=None,
        last_change_summary=None,
    )
    session.add(record)
    session.flush()
    session.add(
        TripPlanRunRecord(
            trip_id=trip_id,
            plan_run_id=plan_run_id,
            created_at=created_at,
        )
    )
    session.flush()
    return record


def append_plan_run(
    session: Session,
    *,
    trip: TripRecord,
    plan_run_id: uuid.UUID,
    created_at: datetime,
    change_summary: dict | None,
) -> None:
    session.add(
        TripPlanRunRecord(
            trip_id=trip.id,
            plan_run_id=plan_run_id,
            created_at=created_at,
        )
    )
    trip.latest_plan_run_id = plan_run_id
    trip.last_activity_at = created_at
    trip.last_change_summary = change_summary


def touch_trip_activity(session: Session, trip: TripRecord, *, at: datetime) -> None:
    trip.last_activity_at = at
    session.flush()


def get_trip_for_capability(
    session: Session,
    trip_id: uuid.UUID,
    capability_id: uuid.UUID,
    *,
    now: datetime,
) -> TripRecord | None:
    record = session.get(TripRecord, trip_id)
    if record is None or record.capability_id != capability_id:
        return None
    if record.deleted_at is not None:
        return None
    if trip_expired(record.last_activity_at, now=now):
        return None
    return record


def list_trips_for_capability(
    session: Session,
    capability_id: uuid.UUID,
    *,
    now: datetime,
) -> list[TripRecord]:
    statement = (
        select(TripRecord)
        .where(TripRecord.capability_id == capability_id)
        .where(TripRecord.deleted_at.is_(None))
        .order_by(TripRecord.last_activity_at.desc())
    )
    trips = list(session.scalars(statement))
    return [trip for trip in trips if not trip_expired(trip.last_activity_at, now=now)]


def soft_delete_trip(session: Session, trip: TripRecord, *, deleted_at: datetime) -> None:
    trip.deleted_at = deleted_at
    session.flush()


def invalidate_share_links_for_trip(
    session: Session,
    trip_id: uuid.UUID,
    *,
    invalidated_at: datetime,
) -> None:
    statement = select(TripShareLinkRecord).where(
        TripShareLinkRecord.trip_id == trip_id,
        TripShareLinkRecord.invalidated_at.is_(None),
    )
    for link in session.scalars(statement):
        link.invalidated_at = invalidated_at


def create_share_link(
    session: Session,
    *,
    link_id: uuid.UUID,
    trip_id: uuid.UUID,
    plan_run_id: uuid.UUID,
    token_hash: str,
    created_at: datetime,
) -> TripShareLinkRecord:
    invalidate_share_links_for_trip(session, trip_id, invalidated_at=created_at)
    record = TripShareLinkRecord(
        id=link_id,
        trip_id=trip_id,
        plan_run_id=plan_run_id,
        token_hash=token_hash,
        created_at=created_at,
        invalidated_at=None,
    )
    session.add(record)
    session.flush()
    return record


def get_active_share_link_by_token_hash(
    session: Session,
    token_hash: str,
    *,
    now: datetime,
) -> TripShareLinkRecord | None:
    statement = select(TripShareLinkRecord).where(
        TripShareLinkRecord.token_hash == token_hash,
        TripShareLinkRecord.invalidated_at.is_(None),
    )
    link = session.scalar(statement)
    if link is None:
        return None
    trip = session.get(TripRecord, link.trip_id)
    if trip is None or trip.deleted_at is not None:
        return None
    if trip_expired(trip.last_activity_at, now=now):
        return None
    return link
