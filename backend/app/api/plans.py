from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.api.schemas.plan import PlanRequest
from app.api.schemas.plan import PlanResponse
from app.planning.service import build_plan
from app.repositories.routes import get_published_route_by_id
from app.repositories.routes import record_to_route

router = APIRouter(tags=["plans"])


@router.post("/routes/{route_id}/plans", response_model=PlanResponse)
def create_plan(
    route_id: uuid.UUID,
    body: PlanRequest,
    session: Session = Depends(get_db_session),
) -> PlanResponse:
    record = get_published_route_by_id(session, route_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Route not found")
    route = record_to_route(session, record)
    _run, payload = build_plan(
        session,
        route=route,
        route_id=route_id,
        plan_date=body.plan_date,
        origin=body.origin,
        start_time_local=body.start_time_local,
    )
    session.commit()
    return PlanResponse(
        plan_run_id=payload["plan_run_id"],
        route_id=payload["route_id"],
        plan_date=payload["plan_date"],
        trailhead_timezone=payload["trailhead_timezone"],
        safety_disclaimer=payload["safety_disclaimer"],
        recommendation=payload["recommendation"],
        confidence=payload["confidence"],
        components=payload["components"],
        weather=payload["weather"],
        gear=payload["gear"],
        daylight=payload["daylight"],
        explanation=payload["explanation"],
        thunderstorm=payload["thunderstorm"],
        transit_summary=payload["transit_summary"],
        origin_region=payload["origin_region"],
    )
