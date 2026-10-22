from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.api.route_search_filters import RouteSearchFilterError
from app.api.route_search_filters import difficulty_values_in_filter
from app.api.route_search_filters import parse_difficulty_filter
from app.api.schemas.route_detail import RouteDetail
from app.api.schemas.route_search import PositiveMinutesQuery
from app.api.schemas.route_search import RouteSearchItem
from app.api.schemas.route_search import RouteSearchResponse
from app.api.schemas.route_search import SeasonMonthQuery
from app.domain.route import RouteType
from app.domain.route import TransitAccessibility
from app.models.route import RouteRecord
from app.repositories.routes import RouteSearchCriteria
from app.repositories.routes import difficulty_from_route_record
from app.repositories.routes import get_published_route_by_id
from app.repositories.routes import record_to_route
from app.repositories.routes import search_routes

router = APIRouter(tags=["routes"])


def _record_to_search_item(record: RouteRecord) -> RouteSearchItem:
    from app.domain.route import Assessment
    from app.domain.route import Completeness
    from app.domain.route import Provenance
    from app.domain.route import Publication
    from app.domain.route import Region
    from app.domain.route import RegionCoverage

    return RouteSearchItem(
        id=record.id,
        name=record.name,
        route_type=RouteType(record.route_type),
        region=Region(
            name=record.region_name,
            country=record.region_country,
            coverage=RegionCoverage(record.region_coverage),
        ),
        publication=Publication(record.publication),
        provenance=Provenance(record.provenance),
        completeness=Completeness(record.completeness),
        assessment=Assessment(record.assessment),
        duration_minutes=record.duration_minutes,
        duration_is_estimated=record.duration_is_estimated,
        transit_accessibility=TransitAccessibility(record.transit_accessibility),
        season_months=sorted(record.season_months),
        difficulty=difficulty_from_route_record(record),
    )


def _record_to_detail(session: Session, record: RouteRecord) -> RouteDetail:
    item = _record_to_search_item(record)
    route = record_to_route(session, record)
    return RouteDetail(
        **item.model_dump(),
        trailhead=route.trailhead,
        linestring=route.linestring,
        gpx=route.gpx,
        elevation_min_m=route.elevation_min_m,
        elevation_max_m=route.elevation_max_m,
        elevation_gain_m=route.elevation_gain_m,
        elevation_loss_m=route.elevation_loss_m,
        approach_minutes=route.approach_minutes,
        technical_minutes=route.technical_minutes,
        descent_minutes=route.descent_minutes,
        season_note=route.season_note,
        description=route.description,
        official_source_links=route.official_source_links,
        closure_assessment=route.closure_assessment,
    )


@router.get("/routes/{route_id}", response_model=RouteDetail)
def get_route_detail(
    route_id: uuid.UUID,
    session: Session = Depends(get_db_session),
) -> RouteDetail:
    record = get_published_route_by_id(session, route_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Route not found")
    return _record_to_detail(session, record)


@router.get("/routes", response_model=RouteSearchResponse)
def list_routes(
    session: Session = Depends(get_db_session),
    region: str | None = Query(default=None),
    country: str | None = Query(default=None, min_length=2, max_length=2),
    route_type: RouteType | None = Query(default=None),
    difficulty_scale: str | None = Query(default=None),
    difficulty_min: str | None = Query(default=None),
    difficulty_max: str | None = Query(default=None),
    duration_min_minutes: PositiveMinutesQuery | None = Query(default=None),
    duration_max_minutes: PositiveMinutesQuery | None = Query(default=None),
    season_month: SeasonMonthQuery | None = Query(default=None),
    transit_accessibility: TransitAccessibility | None = Query(default=None),
) -> RouteSearchResponse:
    if country is not None and (not country.isalpha() or country != country.upper()):
        raise HTTPException(
            status_code=422,
            detail="country must be ISO 3166-1 alpha-2 (two uppercase letters)",
        )

    try:
        difficulty_filter = parse_difficulty_filter(
            route_type=route_type,
            difficulty_scale=difficulty_scale,
            difficulty_min=difficulty_min,
            difficulty_max=difficulty_max,
        )
    except RouteSearchFilterError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    difficulty_values = (
        difficulty_values_in_filter(difficulty_filter) if difficulty_filter else None
    )
    criteria = RouteSearchCriteria(
        region_name=region,
        country=country,
        route_type=route_type,
        difficulty_structured_scale=(
            None if difficulty_filter is None else difficulty_filter.structured_scale
        ),
        difficulty_structured_values=difficulty_values,
        duration_min_minutes=duration_min_minutes,
        duration_max_minutes=duration_max_minutes,
        season_month=season_month,
        transit_accessibility=transit_accessibility,
    )
    records = search_routes(session, criteria)
    return RouteSearchResponse(routes=[_record_to_search_item(record) for record in records])
