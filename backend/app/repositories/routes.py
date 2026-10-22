from __future__ import annotations

import uuid

from geoalchemy2.elements import WKTElement
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


def save_route(session: Session, route: Route) -> uuid.UUID:
    route_id = uuid.uuid4()
    session.add(route_to_record(route, route_id))
    session.flush()
    return route_id


def upsert_route(session: Session, route_id: uuid.UUID, route: Route) -> uuid.UUID:
    incoming = route_to_record(route, route_id)
    existing = session.get(RouteRecord, route_id)
    if existing is None:
        session.add(incoming)
        session.flush()
        return route_id
    for column in RouteRecord.__table__.columns:
        name = column.key
        if name == "id":
            continue
        setattr(existing, name, getattr(incoming, name))
    session.flush()
    return route_id


def get_route(session: Session, route_id: uuid.UUID) -> Route | None:
    record = session.get(RouteRecord, route_id)
    if record is None:
        return None
    return record_to_route(session, record)


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
