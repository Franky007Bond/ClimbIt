from __future__ import annotations

from app.api.schemas.route_search import RouteSearchItem
from app.domain.closure import ClosureAssessment
from app.domain.route import LineString
from app.domain.route import NonNegativeMeters
from app.domain.route import Point
from app.domain.route import PositiveMinutes


class RouteDetail(RouteSearchItem):
    trailhead: Point | None
    linestring: LineString | None
    gpx: str | None
    elevation_min_m: int | None
    elevation_max_m: int | None
    elevation_gain_m: NonNegativeMeters | None
    elevation_loss_m: NonNegativeMeters | None
    approach_minutes: PositiveMinutes | None
    technical_minutes: PositiveMinutes | None
    descent_minutes: PositiveMinutes | None
    season_note: str | None
    description: str
    official_source_links: list[str]
    closure_assessment: ClosureAssessment | None
