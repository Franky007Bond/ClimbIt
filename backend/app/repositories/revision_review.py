from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.closure import ClosureAssessment
from app.domain.difficulty import Difficulty
from app.domain.route import Assessment
from app.domain.route import Completeness
from app.domain.route import LineString
from app.domain.route import Point
from app.domain.route import Provenance
from app.domain.route import Publication
from app.domain.route import Region
from app.domain.route import RegionCoverage
from app.domain.route import Route
from app.domain.route import RouteType
from app.domain.route import TransitAccessibility
from app.models.route import RouteRecord
from app.models.route_revision import RouteRevisionRecord
from app.repositories.routes import upsert_route


@dataclass(frozen=True, slots=True)
class PendingRevisionSummary:
    revision_id: uuid.UUID
    route_id: uuid.UUID
    route_name: str
    revision_number: int
    created_at: datetime
    author_kind: str
    changed_keys: list[str]


@dataclass(frozen=True, slots=True)
class FieldDiff:
    field: str
    before: object
    after: object


class RevisionReviewError(Exception):
    pass


class RevisionNotFound(RevisionReviewError):
    pass


class RevisionNotPending(RevisionReviewError):
    pass


def snapshot_to_route(data: dict) -> Route:
    trailhead = None
    if data.get("trailhead") is not None:
        longitude, latitude = data["trailhead"]["coordinates"]
        trailhead = Point(longitude=longitude, latitude=latitude)
    linestring = None
    if data.get("linestring") is not None:
        points = [
            Point(longitude=coords[0], latitude=coords[1])
            for coords in data["linestring"]["coordinates"]
        ]
        linestring = LineString(points=points)
    difficulty = None
    if data.get("difficulty") is not None:
        difficulty = Difficulty.model_validate(data["difficulty"])
    closure = None
    if data.get("closure_assessment") is not None:
        closure = ClosureAssessment.model_validate(data["closure_assessment"])
    region_data = data["region"]
    return Route(
        name=data["name"],
        route_type=RouteType(data["route_type"]),
        region=Region(
            name=region_data["name"],
            country=region_data["country"],
            coverage=RegionCoverage(region_data["coverage"]),
        ),
        publication=Publication(data["publication"]),
        provenance=Provenance(data["provenance"]),
        completeness=Completeness(data["completeness"]),
        assessment=Assessment(data["assessment"]),
        trailhead=trailhead,
        linestring=linestring,
        gpx=data.get("gpx"),
        elevation_min_m=data.get("elevation_min_m"),
        elevation_max_m=data.get("elevation_max_m"),
        elevation_gain_m=data.get("elevation_gain_m"),
        elevation_loss_m=data.get("elevation_loss_m"),
        duration_minutes=data.get("duration_minutes"),
        approach_minutes=data.get("approach_minutes"),
        technical_minutes=data.get("technical_minutes"),
        descent_minutes=data.get("descent_minutes"),
        duration_is_estimated=data["duration_is_estimated"],
        original_difficulty_value=data.get("original_difficulty_value"),
        original_difficulty_scale=data.get("original_difficulty_scale"),
        difficulty=difficulty,
        closure_assessment=closure,
        season_months=set(data.get("season_months") or []),
        season_note=data.get("season_note"),
        description=data["description"],
        transit_accessibility=TransitAccessibility(data["transit_accessibility"]),
        official_source_links=list(data.get("official_source_links") or []),
    )


def changed_top_level_keys(before: dict | None, after: dict) -> list[str]:
    if before is None:
        return sorted(after.keys())
    keys = set(before) | set(after)
    return sorted(key for key in keys if before.get(key) != after.get(key))


def field_diffs(before: dict | None, after: dict) -> list[FieldDiff]:
    diffs: list[FieldDiff] = []
    for key in changed_top_level_keys(before, after):
        diffs.append(
            FieldDiff(
                field=key,
                before=None if before is None else before.get(key),
                after=after.get(key),
            )
        )
    return diffs


def list_pending_revisions(session: Session) -> list[PendingRevisionSummary]:
    summaries: list[PendingRevisionSummary] = []
    for revision, route_name in session.execute(
        select(RouteRevisionRecord, RouteRecord.name)
        .join(RouteRecord, RouteRecord.id == RouteRevisionRecord.route_id)
        .where(RouteRevisionRecord.application_status == "pending")
        .order_by(RouteRevisionRecord.created_at.asc())
    ).all():
        summaries.append(
            PendingRevisionSummary(
                revision_id=revision.id,
                route_id=revision.route_id,
                route_name=route_name,
                revision_number=revision.revision_number,
                created_at=revision.created_at,
                author_kind=revision.author_kind,
                changed_keys=changed_top_level_keys(
                    revision.before_snapshot,
                    revision.after_snapshot,
                ),
            )
        )
    return summaries


def get_revision_record(session: Session, revision_id: uuid.UUID) -> RouteRevisionRecord:
    revision = session.get(RouteRevisionRecord, revision_id)
    if revision is None:
        raise RevisionNotFound
    return revision


def approve_pending_revision(
    session: Session,
    revision_id: uuid.UUID,
    *,
    maintainer_username: str,
) -> None:
    revision = get_revision_record(session, revision_id)
    if revision.application_status != "pending":
        raise RevisionNotPending
    proposed = snapshot_to_route(revision.after_snapshot)
    upsert_route(
        session,
        revision.route_id,
        proposed,
        author_kind="maintainer",
        author_ref=maintainer_username,
    )
    revision.application_status = "superseded"
    session.flush()


def reject_pending_revision(session: Session, revision_id: uuid.UUID) -> None:
    revision = get_revision_record(session, revision_id)
    if revision.application_status != "pending":
        raise RevisionNotPending
    revision.application_status = "rejected"
    session.flush()
