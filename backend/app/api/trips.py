from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.trip_auth import clear_trip_capability_cookie
from app.trip_auth import invalidate_trip_capability_for_request
from app.trip_auth import issue_trip_capability
from app.trip_auth import read_trip_capability
from app.trip_auth import set_trip_capability_cookie

router = APIRouter(prefix="/trips", tags=["trips"])


class TripCapabilityStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str


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
