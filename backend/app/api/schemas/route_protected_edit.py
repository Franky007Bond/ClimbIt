from pydantic import BaseModel, ConfigDict, model_validator

from app.domain.closure import ClosureAssessment
from app.domain.difficulty import Difficulty
from app.domain.route import Assessment
from app.domain.route import Completeness
from app.domain.route import LineString
from app.domain.route import NonNegativeMeters
from app.domain.route import Point
from app.domain.route import PositiveMinutes
from app.domain.route import Provenance
from app.domain.route import Publication
from app.domain.route import Region
from app.domain.route import Route
from app.domain.route import RouteType
from app.domain.route import TransitAccessibility


class ProtectedEditRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_revision_number: int
    name: str | None = None
    route_type: RouteType | None = None
    region: Region | None = None
    trailhead: Point | None = None
    linestring: LineString | None = None
    gpx: str | None = None
    elevation_min_m: int | None = None
    elevation_max_m: int | None = None
    elevation_gain_m: NonNegativeMeters | None = None
    elevation_loss_m: NonNegativeMeters | None = None
    duration_minutes: PositiveMinutes | None = None
    approach_minutes: PositiveMinutes | None = None
    technical_minutes: PositiveMinutes | None = None
    descent_minutes: PositiveMinutes | None = None
    duration_is_estimated: bool | None = None
    original_difficulty_value: str | None = None
    original_difficulty_scale: str | None = None
    difficulty: Difficulty | None = None
    closure_assessment: ClosureAssessment | None = None
    season_months: set[int] | None = None
    transit_accessibility: TransitAccessibility | None = None
    official_source_links: list[str] | None = None
    publication: Publication | None = None
    deleted: bool | None = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> ProtectedEditRequest:
        protected_fields = self.model_fields_set - {"base_revision_number"}
        if not protected_fields:
            raise ValueError("at least one protected field is required")
        return self

    def merge_onto(self, current: Route) -> Route:
        base = current.model_dump(mode="python")
        for key in self.model_fields_set:
            if key in {"deleted", "base_revision_number"}:
                continue
            base[key] = getattr(self, key)
        if "deleted" in self.model_fields_set and self.deleted:
            base["publication"] = Publication.UNPUBLISHED
        return Route.model_validate(base)


class ProtectedEditResponse(BaseModel):
    revision_id: str
    revision_number: int
    application_status: str
