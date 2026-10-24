from __future__ import annotations

from datetime import datetime
from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.api.schemas.trips import SharedPlanSnapshot
from app.api.trip_snapshots import sanitized_shared_snapshot
from app.repositories.plan_runs import get_plan_run
from app.repositories.trips import get_active_share_link_by_token_hash
from app.trip_share_tokens import hash_share_token

router = APIRouter(prefix="/shares", tags=["shares"])


@router.get("/{share_token}", response_model=SharedPlanSnapshot)
def get_shared_plan(
    share_token: str,
    session: Session = Depends(get_db_session),
) -> SharedPlanSnapshot:
    now = datetime.now(timezone.utc)
    link = get_active_share_link_by_token_hash(
        session,
        hash_share_token(share_token),
        now=now,
    )
    if link is None:
        raise HTTPException(status_code=404, detail="Share link not found")
    run = get_plan_run(session, link.plan_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Plan run not found")
    snapshot = sanitized_shared_snapshot(
        plan_run_id=str(run.id),
        route_id=str(run.route_id),
        input_snapshot=run.input_snapshot,
        result=run.result,
    )
    if "origin" in run.input_snapshot:
        raise HTTPException(status_code=500, detail="Shared snapshot would leak origin")
    payload_text = str(snapshot)
    forbidden = ("climbit_trip_capability", "capability_id")
    if any(marker in payload_text for marker in forbidden):
        raise HTTPException(
            status_code=500, detail="Shared snapshot would leak capability"
        )
    return SharedPlanSnapshot(**snapshot)
