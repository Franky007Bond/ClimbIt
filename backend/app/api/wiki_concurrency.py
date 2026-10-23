from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.repositories.routes import current_applied_revision_number
from app.repositories.routes import get_published_route_by_id
from app.repositories.routes import record_to_route


def ensure_revision_base(
    session: Session,
    route_id: uuid.UUID,
    base_revision_number: int,
) -> int:
    current = current_applied_revision_number(session, route_id)
    if current is None:
        raise HTTPException(status_code=500, detail="route has no applied revision")
    if base_revision_number > current:
        raise HTTPException(status_code=422, detail="base_revision_number is ahead of applied head")
    if base_revision_number < current:
        record = get_published_route_by_id(session, route_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Route not found")
        route = record_to_route(session, record)
        raise HTTPException(
            status_code=409,
            detail={
                "code": "revision_conflict",
                "current_base_revision_number": current,
                "route_id": str(route_id),
                "published": {
                    "description": route.description,
                    "season_note": route.season_note,
                    "name": route.name,
                    "route_type": route.route_type.value,
                    "original_difficulty_value": route.original_difficulty_value,
                    "original_difficulty_scale": route.original_difficulty_scale,
                },
            },
        )
    return current
