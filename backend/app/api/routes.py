from __future__ import annotations

import os
import uuid

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, Request, UploadFile
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.api.wiki_concurrency import ensure_revision_base
from app.api.wiki_rate_limit import enforce_wiki_anonymous_rate_limit
from app.api.schemas.route_descriptive_edit import DescriptiveEditRequest
from app.api.schemas.route_descriptive_edit import DescriptiveEditResponse
from app.api.schemas.route_protected_edit import ProtectedEditRequest
from app.api.schemas.route_protected_edit import ProtectedEditResponse
from app.api.route_search_filters import RouteSearchFilterError
from app.api.route_search_filters import difficulty_values_in_filter
from app.api.route_search_filters import parse_difficulty_filter
from app.api.schemas.gpx_upload import GpxUploadResponse
from app.api.schemas.route_detail import RouteDetail
from app.api.schemas.route_search import PositiveMinutesQuery
from app.api.schemas.route_search import RouteSearchItem
from app.api.schemas.route_search import RouteSearchResponse
from app.api.schemas.route_search import SeasonMonthQuery
from app.domain.route import Assessment
from app.domain.route import Completeness
from app.domain.route import Provenance
from app.domain.route import Publication
from app.domain.route import Region
from app.domain.route import RegionCoverage
from app.domain.route import Route
from app.domain.route import RouteType
from app.domain.route import TransitAccessibility
from app.gpx.process import GPX_DEFAULT_DESCRIPTION
from app.gpx.process import GpxValidationError
from app.gpx.process import process_gpx_upload
from app.models.route import RouteRecord
from app.repositories.routes import RouteSearchCriteria
from app.repositories.routes import _point_from_element
from app.repositories.routes import difficulty_from_route_record
from app.repositories.routes import get_published_route_by_id
from app.repositories.routes import record_to_route
from app.repositories.routes import apply_descriptive_edit
from app.security.free_text import sanitize_free_text
from app.repositories.routes import save_route
from app.repositories.routes import search_routes
from app.repositories.routes import submit_protected_edit

router = APIRouter(tags=["routes"])

_DEFAULT_MAX_GPX_UPLOAD_BYTES = 10 * 1024 * 1024


def _max_gpx_upload_bytes() -> int:
    raw = os.environ.get("MAX_GPX_UPLOAD_BYTES", str(_DEFAULT_MAX_GPX_UPLOAD_BYTES))
    return int(raw)


def _normalize_gpx_form_description(description: str | None) -> str:
    if description is None:
        return GPX_DEFAULT_DESCRIPTION
    stripped = sanitize_free_text(description)
    if not stripped:
        raise HTTPException(status_code=422, detail="description must be non-empty after strip")
    return stripped


def _normalize_gpx_form_region(name: str, country: str) -> Region:
    try:
        return Region(name=name, country=country, coverage=RegionCoverage.UNSUPPORTED)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc


@router.post(
    "/routes/gpx-upload",
    response_model=GpxUploadResponse,
    status_code=201,
)
async def post_gpx_upload(
    request: Request,
    file: UploadFile = File(...),
    name: str = Form(...),
    route_type: RouteType = Form(...),
    region_name: str = Form(...),
    region_country: str = Form(...),
    description: str | None = Form(default=None),
    session: Session = Depends(get_db_session),
    x_climbit_anonymous_id: str | None = Header(default=None, alias="X-ClimbIt-Anonymous-Id"),
) -> GpxUploadResponse:
    enforce_wiki_anonymous_rate_limit(request)
    raw = await file.read()
    if len(raw) > _max_gpx_upload_bytes():
        raise HTTPException(status_code=413, detail="GPX file exceeds maximum upload size")

    try:
        processed = process_gpx_upload(raw)
    except GpxValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    route_name = name.strip()
    if not route_name:
        raise HTTPException(status_code=422, detail="name must be non-empty after strip")

    region = _normalize_gpx_form_region(region_name, region_country)
    stored_description = _normalize_gpx_form_description(description)

    route = Route(
        name=route_name,
        route_type=route_type,
        region=region,
        publication=Publication.QUARANTINED,
        trailhead=processed.trailhead,
        linestring=processed.linestring,
        gpx=processed.gpx_xml,
        elevation_min_m=processed.elevation_min_m,
        elevation_max_m=processed.elevation_max_m,
        elevation_gain_m=processed.elevation_gain_m,
        elevation_loss_m=processed.elevation_loss_m,
        duration_minutes=None,
        approach_minutes=None,
        technical_minutes=None,
        descent_minutes=None,
        duration_is_estimated=False,
        original_difficulty_value=None,
        original_difficulty_scale=None,
        difficulty=None,
        closure_assessment=None,
        season_months=set(),
        season_note=None,
        description=stored_description,
        transit_accessibility=TransitAccessibility.UNKNOWN,
        official_source_links=[],
        provenance=Provenance.GPX_UPLOAD,
        completeness=Completeness.INCOMPLETE,
        assessment=Assessment.UNASSESSED,
    )

    author_ref = None
    if x_climbit_anonymous_id is not None:
        stripped = x_climbit_anonymous_id.strip()
        author_ref = stripped or None

    route_id = save_route(
        session,
        route,
        author_kind="anonymous",
        author_ref=author_ref,
    )
    session.commit()
    return GpxUploadResponse(
        id=route_id,
        publication=Publication.QUARANTINED,
        provenance=Provenance.GPX_UPLOAD,
    )


def _record_to_search_item(session: Session, record: RouteRecord) -> RouteSearchItem:
    from app.domain.route import Assessment
    from app.domain.route import Completeness
    from app.domain.route import Provenance
    from app.domain.route import Publication
    from app.domain.route import Region
    from app.domain.route import RegionCoverage

    trailhead = _point_from_element(session, record.trailhead)
    if trailhead is None:
        msg = f"published route {record.id} is missing trailhead"
        raise ValueError(msg)

    return RouteSearchItem(
        id=record.id,
        name=record.name,
        route_type=RouteType(record.route_type),
        trailhead=trailhead,
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
    from datetime import datetime
    from datetime import timezone

    from app.domain.closure import effective_closure_status
    from app.routes.elevation_profile import build_elevation_profile
    from app.routes.trailhead_transit import resolve_trailhead_transit_connection

    item = _record_to_search_item(session, record)
    route = record_to_route(session, record)
    now = datetime.now(timezone.utc)
    closure_effective = None
    if route.closure_assessment is not None:
        closure_effective = effective_closure_status(route.closure_assessment, now)
    return RouteDetail(
        **item.model_dump(),
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
        closure_effective_status=closure_effective,
        elevation_profile=_elevation_profile_response(build_elevation_profile(route)),
        trailhead_transit_connection=_trailhead_transit_response(
            resolve_trailhead_transit_connection(route)
        ),
    )


def _elevation_profile_response(profile: object):
    from app.api.schemas.route_visualization import ElevationProfile
    from app.api.schemas.route_visualization import ElevationProfilePoint
    from app.routes.elevation_profile import ElevationProfile as DomainProfile

    if not isinstance(profile, DomainProfile):
        return None
    return ElevationProfile(
        synthesized=profile.synthesized,
        points=[
            ElevationProfilePoint(distance_m=point.distance_m, elevation_m=point.elevation_m)
            for point in profile.points
        ],
    )


def _trailhead_transit_response(connection: object):
    from app.api.schemas.route_visualization import TrailheadTransitConnection
    from app.routes.trailhead_transit import TrailheadTransitConnection as DomainConnection

    if not isinstance(connection, DomainConnection):
        return None
    return TrailheadTransitConnection(
        hub_id=connection.hub_id,
        stop_name=connection.stop_name,
        latitude=connection.latitude,
        longitude=connection.longitude,
        distance_m=connection.distance_m,
    )


def _normalize_descriptive_edit(body: DescriptiveEditRequest) -> tuple[str | None, str | None, bool, bool]:
    update_description = "description" in body.model_fields_set
    update_season_note = "season_note" in body.model_fields_set
    description: str | None = None
    season_note: str | None = None
    if update_description:
        if body.description is None:
            raise HTTPException(status_code=422, detail="description must be a non-empty string")
        description = sanitize_free_text(body.description)
        if not description:
            raise HTTPException(
                status_code=422,
                detail="description must be non-empty after strip",
            )
    if update_season_note:
        if body.season_note is None:
            season_note = None
        else:
            season_note = sanitize_free_text(body.season_note)
            if not season_note:
                raise HTTPException(
                    status_code=422,
                    detail="season_note must be non-empty after strip",
                )
    return description, season_note, update_description, update_season_note


@router.patch(
    "/routes/{route_id}/descriptive",
    response_model=DescriptiveEditResponse,
)
def patch_route_descriptive(
    route_id: uuid.UUID,
    body: DescriptiveEditRequest,
    request: Request,
    session: Session = Depends(get_db_session),
    x_climbit_anonymous_id: str | None = Header(default=None, alias="X-ClimbIt-Anonymous-Id"),
) -> DescriptiveEditResponse:
    enforce_wiki_anonymous_rate_limit(request)
    try:
        description, season_note, update_description, update_season_note = (
            _normalize_descriptive_edit(body)
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    ensure_revision_base(session, route_id, body.base_revision_number)

    author_ref = None
    if x_climbit_anonymous_id is not None:
        stripped = x_climbit_anonymous_id.strip()
        author_ref = stripped or None

    try:
        revision_number, stored_description, stored_season_note = apply_descriptive_edit(
            session,
            route_id,
            description=description,
            season_note=season_note,
            update_description=update_description,
            update_season_note=update_season_note,
            author_ref=author_ref,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Route not found") from exc

    session.commit()
    return DescriptiveEditResponse(
        revision_number=revision_number,
        description=stored_description,
        season_note=stored_season_note,
    )


@router.post(
    "/routes/{route_id}/protected-edits",
    response_model=ProtectedEditResponse,
    status_code=201,
)
def post_route_protected_edit(
    route_id: uuid.UUID,
    body: ProtectedEditRequest,
    request: Request,
    session: Session = Depends(get_db_session),
    x_climbit_anonymous_id: str | None = Header(default=None, alias="X-ClimbIt-Anonymous-Id"),
) -> ProtectedEditResponse:
    enforce_wiki_anonymous_rate_limit(request)
    record = get_published_route_by_id(session, route_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Route not found")
    ensure_revision_base(session, route_id, body.base_revision_number)
    current = record_to_route(session, record)
    try:
        proposed = body.merge_onto(current)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=[{"type": error["type"], "msg": error["msg"]} for error in exc.errors()],
        ) from exc

    author_ref = None
    if x_climbit_anonymous_id is not None:
        stripped = x_climbit_anonymous_id.strip()
        author_ref = stripped or None

    try:
        revision_id, revision_number = submit_protected_edit(
            session,
            route_id,
            proposed,
            author_ref=author_ref,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Route not found") from exc

    session.commit()
    return ProtectedEditResponse(
        revision_id=str(revision_id),
        revision_number=revision_number,
        application_status="pending",
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
    return RouteSearchResponse(
        routes=[_record_to_search_item(session, record) for record in records]
    )
