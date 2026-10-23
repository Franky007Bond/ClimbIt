from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from datetime import timezone

from geoalchemy2.elements import WKTElement
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.closure import ClosureAssessment
from app.domain.closure import ClosureReviewStatus
from app.domain.closure import ClosureStatus
from app.domain.difficulty import Difficulty
from app.domain.difficulty import MappingConfidence
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

_AUTHOR_KINDS = frozenset({"system", "anonymous", "maintainer"})


@dataclass(frozen=True, slots=True)
class RouteRevision:
    revision_number: int
    created_at: datetime
    author_kind: str
    author_ref: str | None
    before_snapshot: dict | None
    after_snapshot: dict
    application_status: str


@dataclass(frozen=True, slots=True)
class RouteSearchCriteria:
    region_name: str | None = None
    country: str | None = None
    route_type: RouteType | None = None
    difficulty_structured_scale: str | None = None
    difficulty_structured_values: list[str] | None = None
    duration_min_minutes: int | None = None
    duration_max_minutes: int | None = None
    season_month: int | None = None
    transit_accessibility: TransitAccessibility | None = None


def search_routes(session: Session, criteria: RouteSearchCriteria) -> list[RouteRecord]:
    statement = select(RouteRecord).where(
        RouteRecord.publication == Publication.PUBLISHED.value
    )
    if criteria.region_name is not None:
        normalized = criteria.region_name.strip()
        statement = statement.where(RouteRecord.region_name == normalized)
    if criteria.country is not None:
        statement = statement.where(RouteRecord.region_country == criteria.country)
    if criteria.route_type is not None:
        statement = statement.where(RouteRecord.route_type == criteria.route_type.value)
    if criteria.transit_accessibility is not None:
        statement = statement.where(
            RouteRecord.transit_accessibility == criteria.transit_accessibility.value
        )
    if criteria.duration_min_minutes is not None:
        statement = statement.where(
            RouteRecord.duration_minutes >= criteria.duration_min_minutes
        )
    if criteria.duration_max_minutes is not None:
        statement = statement.where(
            RouteRecord.duration_minutes <= criteria.duration_max_minutes
        )
    if criteria.season_month is not None:
        statement = statement.where(
            RouteRecord.season_months.contains([criteria.season_month])
        )
    if criteria.difficulty_structured_scale is not None:
        statement = statement.where(
            RouteRecord.difficulty_structured_scale == criteria.difficulty_structured_scale
        )
        if criteria.difficulty_structured_values is not None:
            statement = statement.where(
                RouteRecord.difficulty_structured_value.in_(
                    criteria.difficulty_structured_values
                )
            )
    statement = statement.order_by(RouteRecord.name.asc(), RouteRecord.id.asc())
    return list(session.scalars(statement).all())


def get_published_route_by_id(session: Session, route_id: uuid.UUID) -> RouteRecord | None:
    statement = select(RouteRecord).where(
        RouteRecord.id == route_id,
        RouteRecord.publication == Publication.PUBLISHED.value,
    )
    return session.scalar(statement)


def save_route(
    session: Session,
    route: Route,
    *,
    author_kind: str = "system",
    author_ref: str | None = None,
) -> uuid.UUID:
    route_id = uuid.uuid4()
    session.add(route_to_record(route, route_id))
    session.flush()
    _append_route_revision(
        session,
        route_id=route_id,
        before_snapshot=None,
        after_snapshot=route_snapshot(route),
        author_kind=author_kind,
        author_ref=author_ref,
    )
    return route_id


def upsert_route(
    session: Session,
    route_id: uuid.UUID,
    route: Route,
    *,
    author_kind: str = "system",
    author_ref: str | None = None,
) -> uuid.UUID:
    existing = session.get(RouteRecord, route_id)
    if existing is None:
        session.add(route_to_record(route, route_id))
        session.flush()
        _append_route_revision(
            session,
            route_id=route_id,
            before_snapshot=None,
            after_snapshot=route_snapshot(route),
            author_kind=author_kind,
            author_ref=author_ref,
        )
        return route_id
    current = record_to_route(session, existing)
    if route_snapshot(current) == route_snapshot(route):
        return route_id
    before_snapshot = route_snapshot(current)
    incoming = route_to_record(route, route_id)
    for column in RouteRecord.__table__.columns:
        name = column.key
        if name == "id":
            continue
        setattr(existing, name, getattr(incoming, name))
    session.flush()
    _append_route_revision(
        session,
        route_id=route_id,
        before_snapshot=before_snapshot,
        after_snapshot=route_snapshot(route),
        author_kind=author_kind,
        author_ref=author_ref,
    )
    return route_id


def apply_descriptive_edit(
    session: Session,
    route_id: uuid.UUID,
    *,
    description: str | None = None,
    season_note: str | None = None,
    update_description: bool = False,
    update_season_note: bool = False,
    author_ref: str | None = None,
) -> tuple[int, str, str | None]:
    record = get_published_route_by_id(session, route_id)
    if record is None:
        msg = "route not found"
        raise LookupError(msg)
    route = record_to_route(session, record)
    updates: dict[str, object] = {}
    if update_description:
        assert description is not None
        updates["description"] = description
    if update_season_note:
        updates["season_note"] = season_note
    updated = route.model_copy(update=updates)
    upsert_route(
        session,
        route_id,
        updated,
        author_kind="anonymous",
        author_ref=author_ref,
    )
    revisions = list_route_revisions(session, route_id)
    if not revisions:
        msg = "expected revision after descriptive edit"
        raise RuntimeError(msg)
    latest = revisions[-1]
    return latest.revision_number, updated.description, updated.season_note


def list_route_revisions(session: Session, route_id: uuid.UUID) -> list[RouteRevision]:
    rows = session.scalars(
        select(RouteRevisionRecord)
        .where(RouteRevisionRecord.route_id == route_id)
        .order_by(RouteRevisionRecord.revision_number.asc())
    ).all()
    return [
        RouteRevision(
            revision_number=row.revision_number,
            created_at=row.created_at,
            author_kind=row.author_kind,
            author_ref=row.author_ref,
            before_snapshot=row.before_snapshot,
            after_snapshot=row.after_snapshot,
            application_status=row.application_status,
        )
        for row in rows
    ]


def get_route(session: Session, route_id: uuid.UUID) -> Route | None:
    record = session.get(RouteRecord, route_id)
    if record is None:
        return None
    return record_to_route(session, record)


def route_snapshot(route: Route) -> dict:
    difficulty = None
    if route.difficulty is not None:
        difficulty = route.difficulty.model_dump(mode="json")
    closure = None
    if route.closure_assessment is not None:
        closure = route.closure_assessment.model_dump(mode="json")
    return {
        "name": route.name,
        "route_type": route.route_type.value,
        "region": {
            "name": route.region.name,
            "country": route.region.country,
            "coverage": route.region.coverage.value,
        },
        "publication": route.publication.value,
        "provenance": route.provenance.value,
        "completeness": route.completeness.value,
        "assessment": route.assessment.value,
        "trailhead": _point_geojson(route.trailhead),
        "linestring": _linestring_geojson(route.linestring),
        "gpx": route.gpx,
        "elevation_min_m": route.elevation_min_m,
        "elevation_max_m": route.elevation_max_m,
        "elevation_gain_m": route.elevation_gain_m,
        "elevation_loss_m": route.elevation_loss_m,
        "duration_minutes": route.duration_minutes,
        "approach_minutes": route.approach_minutes,
        "technical_minutes": route.technical_minutes,
        "descent_minutes": route.descent_minutes,
        "duration_is_estimated": route.duration_is_estimated,
        "original_difficulty_value": route.original_difficulty_value,
        "original_difficulty_scale": route.original_difficulty_scale,
        "difficulty": difficulty,
        "closure_assessment": closure,
        "season_months": sorted(route.season_months),
        "season_note": route.season_note,
        "description": route.description,
        "transit_accessibility": route.transit_accessibility.value,
        "official_source_links": list(route.official_source_links),
    }


def _append_route_revision(
    session: Session,
    *,
    route_id: uuid.UUID,
    before_snapshot: dict | None,
    after_snapshot: dict,
    author_kind: str,
    author_ref: str | None,
    application_status: str = "applied",
) -> tuple[uuid.UUID, int]:
    if author_kind not in _AUTHOR_KINDS:
        raise ValueError(f"unsupported author_kind: {author_kind}")
    if application_status not in {"applied", "pending"}:
        raise ValueError(f"unsupported application_status: {application_status}")
    max_number = session.scalar(
        select(func.max(RouteRevisionRecord.revision_number)).where(
            RouteRevisionRecord.route_id == route_id
        )
    )
    revision_number = 1 if max_number is None else max_number + 1
    revision_id = uuid.uuid4()
    session.add(
        RouteRevisionRecord(
            id=revision_id,
            route_id=route_id,
            revision_number=revision_number,
            created_at=datetime.now(timezone.utc),
            author_kind=author_kind,
            author_ref=author_ref,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            application_status=application_status,
        )
    )
    session.flush()
    return revision_id, revision_number


def submit_protected_edit(
    session: Session,
    route_id: uuid.UUID,
    proposed: Route,
    *,
    author_ref: str | None = None,
) -> tuple[uuid.UUID, int]:
    record = get_published_route_by_id(session, route_id)
    if record is None:
        msg = "route not found"
        raise LookupError(msg)
    current = record_to_route(session, record)
    before_snapshot = route_snapshot(current)
    after_snapshot = route_snapshot(proposed)
    revision_id, revision_number = _append_route_revision(
        session,
        route_id=route_id,
        before_snapshot=before_snapshot,
        after_snapshot=after_snapshot,
        author_kind="anonymous",
        author_ref=author_ref,
        application_status="pending",
    )
    return revision_id, revision_number


def _point_geojson(point: Point | None) -> dict | None:
    if point is None:
        return None
    return {"type": "Point", "coordinates": [point.longitude, point.latitude]}


def _linestring_geojson(line: LineString | None) -> dict | None:
    if line is None:
        return None
    return {
        "type": "LineString",
        "coordinates": [[point.longitude, point.latitude] for point in line.points],
    }


def route_to_record(route: Route, route_id: uuid.UUID) -> RouteRecord:
    difficulty = route.difficulty
    closure = route.closure_assessment
    return RouteRecord(
        id=route_id,
        name=route.name,
        route_type=route.route_type.value,
        region_name=route.region.name,
        region_country=route.region.country,
        region_coverage=route.region.coverage.value,
        publication=route.publication.value,
        trailhead=_point_element(route.trailhead),
        linestring=_linestring_element(route.linestring),
        gpx=route.gpx,
        elevation_min_m=route.elevation_min_m,
        elevation_max_m=route.elevation_max_m,
        elevation_gain_m=route.elevation_gain_m,
        elevation_loss_m=route.elevation_loss_m,
        duration_minutes=route.duration_minutes,
        approach_minutes=route.approach_minutes,
        technical_minutes=route.technical_minutes,
        descent_minutes=route.descent_minutes,
        duration_is_estimated=route.duration_is_estimated,
        original_difficulty_value=route.original_difficulty_value,
        original_difficulty_scale=route.original_difficulty_scale,
        difficulty_route_type=None if difficulty is None else difficulty.route_type.value,
        difficulty_original_value=None if difficulty is None else difficulty.original_value,
        difficulty_original_scale=None if difficulty is None else difficulty.original_scale,
        difficulty_structured_scale=None if difficulty is None else difficulty.structured_scale,
        difficulty_structured_value=None if difficulty is None else difficulty.structured_value,
        difficulty_mapped_huebler=None if difficulty is None else difficulty.mapped_huebler,
        difficulty_mapping_confidence=(
            None if difficulty is None else difficulty.mapping_confidence.value
        ),
        difficulty_mapping_source=None if difficulty is None else difficulty.mapping_source,
        difficulty_mapping_citation=None if difficulty is None else difficulty.mapping_citation,
        difficulty_mapping_version=None if difficulty is None else difficulty.mapping_version,
        closure_status=None if closure is None else closure.status.value,
        closure_source_url=None if closure is None else closure.source_url,
        closure_owner=None if closure is None else closure.owner,
        closure_review_status=None if closure is None else closure.review_status.value,
        closure_created_at=None if closure is None else closure.created_at,
        closure_updated_at=None if closure is None else closure.updated_at,
        closure_reviewed_at=None if closure is None else closure.reviewed_at,
        closure_expires_at=None if closure is None else closure.expires_at,
        season_months=sorted(route.season_months),
        season_note=route.season_note,
        description=route.description,
        transit_accessibility=route.transit_accessibility.value,
        official_source_links=list(route.official_source_links),
        provenance=route.provenance.value,
        completeness=route.completeness.value,
        assessment=route.assessment.value,
    )


def record_to_route(session: Session, record: RouteRecord) -> Route:
    return Route(
        name=record.name,
        route_type=RouteType(record.route_type),
        region=Region(
            name=record.region_name,
            country=record.region_country,
            coverage=RegionCoverage(record.region_coverage),
        ),
        publication=Publication(record.publication),
        trailhead=_point_from_element(session, record.trailhead),
        linestring=_linestring_from_element(session, record.linestring),
        gpx=record.gpx,
        elevation_min_m=record.elevation_min_m,
        elevation_max_m=record.elevation_max_m,
        elevation_gain_m=record.elevation_gain_m,
        elevation_loss_m=record.elevation_loss_m,
        duration_minutes=record.duration_minutes,
        approach_minutes=record.approach_minutes,
        technical_minutes=record.technical_minutes,
        descent_minutes=record.descent_minutes,
        duration_is_estimated=record.duration_is_estimated,
        original_difficulty_value=record.original_difficulty_value,
        original_difficulty_scale=record.original_difficulty_scale,
        difficulty=_difficulty_from_record(record),
        closure_assessment=_closure_from_record(record),
        season_months=set(record.season_months),
        season_note=record.season_note,
        description=record.description,
        transit_accessibility=TransitAccessibility(record.transit_accessibility),
        official_source_links=list(record.official_source_links),
        provenance=Provenance(record.provenance),
        completeness=Completeness(record.completeness),
        assessment=Assessment(record.assessment),
    )


def _point_element(point: Point | None) -> WKTElement | None:
    if point is None:
        return None
    return WKTElement(f"POINT({point.longitude} {point.latitude})", srid=4326)


def _linestring_element(line: LineString | None) -> WKTElement | None:
    if line is None:
        return None
    coords = ", ".join(f"{point.longitude} {point.latitude}" for point in line.points)
    return WKTElement(f"LINESTRING({coords})", srid=4326)


def _geom_as_text(session: Session, geom: object) -> str | None:
    if geom is None:
        return None
    return session.scalar(select(geom.ST_AsText()))


def _wkt_coordinates(wkt: str, kind: str) -> list[tuple[float, float]]:
    text = wkt.strip()
    if text.upper().startswith("SRID="):
        text = text.split(";", 1)[1]
    prefix = kind.upper()
    if not text.upper().startswith(prefix):
        raise ValueError("geometry WKT did not round-trip")
    inner = text[text.find("(") + 1 : text.rfind(")")]
    pairs: list[tuple[float, float]] = []
    for part in inner.split(","):
        items = part.split()
        if len(items) != 2:
            raise ValueError("geometry WKT did not round-trip")
        pairs.append((float(items[0]), float(items[1])))
    return pairs


def _point_from_element(session: Session, geom: object) -> Point | None:
    wkt = _geom_as_text(session, geom)
    if wkt is None:
        return None
    pairs = _wkt_coordinates(wkt, "POINT")
    if len(pairs) != 1:
        raise ValueError("point WKT did not round-trip")
    longitude, latitude = pairs[0]
    return Point(longitude=longitude, latitude=latitude)


def _linestring_from_element(session: Session, geom: object) -> LineString | None:
    wkt = _geom_as_text(session, geom)
    if wkt is None:
        return None
    pairs = _wkt_coordinates(wkt, "LINESTRING")
    return LineString(points=[Point(longitude=lon, latitude=lat) for lon, lat in pairs])


def difficulty_from_route_record(record: RouteRecord) -> Difficulty | None:
    return _difficulty_from_record(record)


def _difficulty_from_record(record: RouteRecord) -> Difficulty | None:
    if record.difficulty_mapping_confidence is None:
        return None
    return Difficulty(
        route_type=RouteType(record.difficulty_route_type),
        original_value=record.difficulty_original_value,
        original_scale=record.difficulty_original_scale,
        structured_scale=record.difficulty_structured_scale,
        structured_value=record.difficulty_structured_value,
        mapped_huebler=record.difficulty_mapped_huebler,
        mapping_confidence=MappingConfidence(record.difficulty_mapping_confidence),
        mapping_source=record.difficulty_mapping_source,
        mapping_citation=record.difficulty_mapping_citation,
        mapping_version=record.difficulty_mapping_version,
    )


def _closure_from_record(record: RouteRecord) -> ClosureAssessment | None:
    if record.closure_status is None:
        return None
    return ClosureAssessment(
        status=ClosureStatus(record.closure_status),
        source_url=record.closure_source_url,
        owner=record.closure_owner,
        review_status=ClosureReviewStatus(record.closure_review_status),
        created_at=record.closure_created_at,
        updated_at=record.closure_updated_at,
        reviewed_at=record.closure_reviewed_at,
        expires_at=record.closure_expires_at,
    )
