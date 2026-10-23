from __future__ import annotations

import uuid
from datetime import datetime
from datetime import timezone

from sqlalchemy.orm import Session

from app.domain.plan_run import PlanRun
from app.models.plan_run import PlanRunRecord


def _parse_source_timestamps(raw: dict) -> dict[str, datetime | None]:
    parsed: dict[str, datetime | None] = {}
    for key, value in raw.items():
        if value is None:
            parsed[key] = None
        else:
            parsed[key] = datetime.fromisoformat(value)
    return parsed


def _serialize_source_timestamps(stamps: dict[str, datetime | None]) -> dict[str, str | None]:
    return {
        key: value.isoformat() if value is not None else None for key, value in stamps.items()
    }


def _record_to_domain(record: PlanRunRecord) -> PlanRun:
    return PlanRun(
        id=record.id,
        route_id=record.route_id,
        created_at=record.created_at,
        input_snapshot=dict(record.input_snapshot),
        source_timestamps=_parse_source_timestamps(record.source_timestamps),
        rules_version=record.rules_version,
        mapping_version=record.mapping_version,
        adapter_versions=dict(record.adapter_versions),
        explanation=list(record.explanation),
        result=dict(record.result),
    )


def create_plan_run(session: Session, run: PlanRun) -> uuid.UUID:
    record = PlanRunRecord(
        id=run.id,
        route_id=run.route_id,
        created_at=run.created_at,
        input_snapshot=run.input_snapshot,
        source_timestamps=_serialize_source_timestamps(run.source_timestamps),
        rules_version=run.rules_version,
        mapping_version=run.mapping_version,
        adapter_versions=run.adapter_versions,
        explanation=run.explanation,
        result=run.result,
    )
    session.add(record)
    session.flush()
    return record.id


def get_plan_run(session: Session, run_id: uuid.UUID) -> PlanRun | None:
    record = session.get(PlanRunRecord, run_id)
    if record is None:
        return None
    return _record_to_domain(record)


def new_plan_run_id() -> uuid.UUID:
    return uuid.uuid4()


def plan_run_created_at() -> datetime:
    return datetime.now(timezone.utc)
