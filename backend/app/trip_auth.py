from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime
from datetime import timezone

from fastapi import HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.repositories.trip_capabilities import create_trip_capability
from app.repositories.trip_capabilities import get_trip_capability
from app.repositories.trip_capabilities import invalidate_trip_capability

TRIP_CAPABILITY_COOKIE_NAME = "climbit_trip_capability"


@dataclass(frozen=True, slots=True)
class TripCapability:
    id: uuid.UUID


def _capability_secret() -> str:
    secret = os.environ.get("TRIP_CAPABILITY_SECRET", "").strip()
    if not secret:
        raise HTTPException(
            status_code=503,
            detail={"reason": "trip_capability_unconfigured"},
        )
    return secret


def _sign_payload(payload: str, secret: str) -> str:
    digest = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload}.{digest}"


def create_capability_token(capability_id: uuid.UUID) -> str:
    secret = _capability_secret()
    nonce = secrets.token_urlsafe(16)
    payload = f"{capability_id}:{nonce}"
    return _sign_payload(payload, secret)


def parse_capability_token(token: str, secret: str) -> uuid.UUID | None:
    if "." not in token:
        return None
    payload, digest = token.rsplit(".", 1)
    expected = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(digest, expected):
        return None
    capability_id_raw, _nonce = payload.split(":", 1)
    try:
        return uuid.UUID(capability_id_raw)
    except ValueError:
        return None


def read_trip_capability(request: Request, session: Session) -> TripCapability | None:
    token = request.cookies.get(TRIP_CAPABILITY_COOKIE_NAME)
    if not token:
        return None
    secret = os.environ.get("TRIP_CAPABILITY_SECRET", "").strip()
    if not secret:
        return None
    capability_id = parse_capability_token(token, secret)
    if capability_id is None:
        return None
    record = get_trip_capability(session, capability_id)
    if record is None or record.invalidated_at is not None:
        return None
    return TripCapability(id=capability_id)


def issue_trip_capability(session: Session) -> tuple[TripCapability, str]:
    now = datetime.now(timezone.utc)
    capability_id = uuid.uuid4()
    create_trip_capability(session, capability_id, created_at=now)
    token = create_capability_token(capability_id)
    return TripCapability(id=capability_id), token


def set_trip_capability_cookie(response: Response, request: Request, token: str) -> None:
    response.set_cookie(
        key=TRIP_CAPABILITY_COOKIE_NAME,
        value=token,
        httponly=True,
        path="/",
        samesite="lax",
        secure=request.url.scheme == "https",
    )


def clear_trip_capability_cookie(response: Response, request: Request) -> None:
    response.delete_cookie(
        key=TRIP_CAPABILITY_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
    )


def require_trip_capability(
    request: Request,
    response: Response,
    session: Session,
) -> TripCapability:
    capability = read_trip_capability(request, session)
    if capability is not None:
        return capability
    capability, token = issue_trip_capability(session)
    session.flush()
    set_trip_capability_cookie(response, request, token)
    return capability


def invalidate_trip_capability_for_request(
    request: Request,
    session: Session,
) -> TripCapability | None:
    token = request.cookies.get(TRIP_CAPABILITY_COOKIE_NAME)
    if not token:
        return None
    secret = os.environ.get("TRIP_CAPABILITY_SECRET", "").strip()
    if not secret:
        return None
    capability_id = parse_capability_token(token, secret)
    if capability_id is None:
        return None
    record = get_trip_capability(session, capability_id)
    if record is None or record.invalidated_at is not None:
        return None
    invalidate_trip_capability(session, capability_id, datetime.now(timezone.utc))
    return TripCapability(id=capability_id)
