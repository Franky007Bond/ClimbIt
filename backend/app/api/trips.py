from __future__ import annotations

import uuid
from datetime import datetime
from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.api.schemas.trips import CreateShareLinkResponse
from app.api.schemas.trips import CreateTripRequest
from app.api.schemas.trips import TripDetailResponse
from app.api.schemas.trips import TripListItem
from app.api.schemas.trips import TripListResponse
from app.planning.service import build_plan
from app.repositories.plan_runs import get_plan_run
from app.repositories.routes import get_published_route_by_id
from app.repositories.routes import record_to_route
from app.repositories.trips import append_plan_run
from app.repositories.trips import create_share_link
from app.repositories.trips import create_trip
from app.repositories.trips import get_trip_for_capability
from app.repositories.trips import invalidate_share_links_for_trip
from app.repositories.trips import list_trips_for_capability
from app.repositories.trips import soft_delete_trip
from app.repositories.trips import touch_trip_activity
from app.trip_auth import clear_trip_capability_cookie
from app.trip_auth import invalidate_trip_capability_for_request
from app.trip_auth import issue_trip_capability
from app.trip_auth import read_trip_capability
from app.trip_auth import require_trip_capability
from app.trip_auth import set_trip_capability_cookie
from app.trip_changes import summarize_plan_run_changes
from app.trip_share_tokens import hash_share_token
from app.trip_share_tokens import new_share_token

router = APIRouter(prefix="/trips", tags=["trips"])


class TripCapabilityStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _trip_list_item(session: Session, trip_id: uuid.UUID) -> TripListItem:
    from app.models.trip import TripRecord

    trip = session.get(TripRecord, trip_id)
    assert trip is not None
    run = get_plan_run(session, trip.latest_plan_run_id)
    assert run is not None
    return TripListItem(
        trip_id=str(trip.id),
        route_id=str(trip.route_id),
        latest_plan_run_id=str(trip.latest_plan_run_id),
        plan_date=str(run.input_snapshot.get("plan_date", "")),
        recommendation=str(run.result.get("recommendation", "unknown")),
        last_change_summary=trip.last_change_summary,
    )


@router.get("/capability", response_model=TripCapabilityStatus)
def ensure_trip_capability(
    request: Request,
    response: Response,
    session: Session = Depends(get_db_session),
) -> TripCapabilityStatus:
    capability = read_trip_capability(request, session)
    if capability is None:
        _capability, token = issue_trip_capability(session)
        session.commit()
        set_trip_capability_cookie(response, request, token)
    return TripCapabilityStatus(status="ready")


@router.delete("/capability", status_code=204)
def delete_trip_capability(
    request: Request,
    response: Response,
    session: Session = Depends(get_db_session),
) -> None:
    capability = invalidate_trip_capability_for_request(request, session)
    if capability is None:
        raise HTTPException(status_code=401, detail="Trip capability required")
    session.commit()
    clear_trip_capability_cookie(response, request)


@router.post("", response_model=TripListItem, status_code=201)
def save_trip(
    request: Request,
    response: Response,
    body: CreateTripRequest,
    session: Session = Depends(get_db_session),
) -> TripListItem:
    capability = require_trip_capability(request, response, session)
    try:
        plan_run_id = uuid.UUID(body.plan_run_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid plan_run_id") from exc
    run = get_plan_run(session, plan_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Plan run not found")
    now = _now()
    trip_id = uuid.uuid4()
    create_trip(
        session,
        trip_id=trip_id,
        capability_id=capability.id,
        route_id=run.route_id,
        plan_run_id=plan_run_id,
        created_at=now,
    )
    session.commit()
    return _trip_list_item(session, trip_id)


@router.get("", response_model=TripListResponse)
def list_trips(
    request: Request,
    response: Response,
    session: Session = Depends(get_db_session),
) -> TripListResponse:
    capability = require_trip_capability(request, response, session)
    now = _now()
    trips = list_trips_for_capability(session, capability.id, now=now)
    for trip in trips:
        touch_trip_activity(session, trip, at=now)
    session.commit()
    return TripListResponse(trips=[_trip_list_item(session, trip.id) for trip in trips])


@router.get("/{trip_id}", response_model=TripDetailResponse)
def get_trip(
    trip_id: uuid.UUID,
    request: Request,
    response: Response,
    session: Session = Depends(get_db_session),
) -> TripDetailResponse:
    capability = require_trip_capability(request, response, session)
    now = _now()
    trip = get_trip_for_capability(session, trip_id, capability.id, now=now)
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    touch_trip_activity(session, trip, at=now)
    session.commit()
    run = get_plan_run(session, trip.latest_plan_run_id)
    assert run is not None
    return TripDetailResponse(
        trip_id=str(trip.id),
        route_id=str(trip.route_id),
        latest_plan_run_id=str(trip.latest_plan_run_id),
        plan_date=str(run.input_snapshot.get("plan_date", "")),
        recommendation=str(run.result.get("recommendation", "unknown")),
        confidence=str(run.result.get("confidence", "unknown")),
        last_change_summary=trip.last_change_summary,
        components=dict(run.result.get("components") or {}),
        explanation=list(run.result.get("explanation") or []),
    )


@router.post("/{trip_id}/reevaluate", response_model=TripDetailResponse)
def reevaluate_trip(
    trip_id: uuid.UUID,
    request: Request,
    response: Response,
    session: Session = Depends(get_db_session),
) -> TripDetailResponse:
    capability = require_trip_capability(request, response, session)
    now = _now()
    trip = get_trip_for_capability(session, trip_id, capability.id, now=now)
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    previous_run = get_plan_run(session, trip.latest_plan_run_id)
    if previous_run is None:
        raise HTTPException(status_code=404, detail="Plan run not found")
    record = get_published_route_by_id(session, trip.route_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Route not found")
    route = record_to_route(session, record)
    plan_date_raw = previous_run.input_snapshot.get("plan_date")
    if not isinstance(plan_date_raw, str):
        raise HTTPException(status_code=409, detail="Trip plan date missing")
    from datetime import date
    from datetime import time as time_type

    plan_date = date.fromisoformat(plan_date_raw)
    start_raw = previous_run.input_snapshot.get("start_time_local")
    start_time = time_type.fromisoformat(start_raw) if isinstance(start_raw, str) else None
    origin_region = previous_run.result.get("origin_region")
    origin = origin_region if isinstance(origin_region, str) and origin_region else "unknown"
    _new_run, payload = build_plan(
        session,
        route=route,
        route_id=trip.route_id,
        plan_date=plan_date,
        origin=origin,
        start_time_local=start_time,
        now=now,
    )
    change_summary = summarize_plan_run_changes(previous_run.result, payload)
    new_run_id = uuid.UUID(payload["plan_run_id"])
    append_plan_run(
        session,
        trip=trip,
        plan_run_id=new_run_id,
        created_at=now,
        change_summary=change_summary,
    )
    session.commit()
    new_run = get_plan_run(session, new_run_id)
    assert new_run is not None
    return TripDetailResponse(
        trip_id=str(trip.id),
        route_id=str(trip.route_id),
        latest_plan_run_id=str(trip.latest_plan_run_id),
        plan_date=str(new_run.input_snapshot.get("plan_date", "")),
        recommendation=str(new_run.result.get("recommendation", "unknown")),
        confidence=str(new_run.result.get("confidence", "unknown")),
        last_change_summary=trip.last_change_summary,
        components=dict(new_run.result.get("components") or {}),
        explanation=list(new_run.result.get("explanation") or []),
    )


@router.delete("/{trip_id}", status_code=204)
def delete_trip(
    trip_id: uuid.UUID,
    request: Request,
    response: Response,
    session: Session = Depends(get_db_session),
) -> None:
    capability = require_trip_capability(request, response, session)
    now = _now()
    trip = get_trip_for_capability(session, trip_id, capability.id, now=now)
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    soft_delete_trip(session, trip, deleted_at=now)
    invalidate_share_links_for_trip(session, trip.id, invalidated_at=now)
    session.commit()


@router.post("/{trip_id}/share", response_model=CreateShareLinkResponse)
def create_trip_share_link(
    trip_id: uuid.UUID,
    request: Request,
    response: Response,
    session: Session = Depends(get_db_session),
) -> CreateShareLinkResponse:
    capability = require_trip_capability(request, response, session)
    now = _now()
    trip = get_trip_for_capability(session, trip_id, capability.id, now=now)
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    token = new_share_token()
    create_share_link(
        session,
        link_id=uuid.uuid4(),
        trip_id=trip.id,
        plan_run_id=trip.latest_plan_run_id,
        token_hash=hash_share_token(token),
        created_at=now,
    )
    touch_trip_activity(session, trip, at=now)
    session.commit()
    return CreateShareLinkResponse(share_token=token)
