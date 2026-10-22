from enum import StrEnum
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    TypeAdapter,
    field_validator,
    model_validator,
)

_HTTP_URL = TypeAdapter(HttpUrl)

PositiveMinutes = Annotated[int, Field(gt=0)]
NonNegativeMeters = Annotated[int, Field(ge=0)]


class Publication(StrEnum):
    QUARANTINED = "quarantined"
    PENDING_REVIEW = "pending_review"
    PUBLISHED = "published"
    UNPUBLISHED = "unpublished"


class Provenance(StrEnum):
    SEED = "seed"
    OSM = "osm"
    GPX_UPLOAD = "gpx_upload"
    MAINTAINER = "maintainer"
    USER = "user"


class Completeness(StrEnum):
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"


class Assessment(StrEnum):
    UNASSESSED = "unassessed"
    CURRENT = "current"
    STALE = "stale"


class RegionCoverage(StrEnum):
    SUPPORTED = "supported"
    SAMPLE = "sample"
    UNSUPPORTED = "unsupported"


class RouteType(StrEnum):
    KLETTERSTEIG = "klettersteig"
    ALPINE_HIKE = "alpine_hike"
    OUTDOOR_CLIMBING = "outdoor_climbing"


class TransitAccessibility(StrEnum):
    TRANSIT_FRIENDLY = "transit_friendly"
    LIMITED = "limited"
    UNKNOWN = "unknown"


class Point(BaseModel):
    model_config = ConfigDict(extra="forbid")

    longitude: Annotated[float, Field(ge=-180, le=180)]
    latitude: Annotated[float, Field(ge=-90, le=90)]


class LineString(BaseModel):
    model_config = ConfigDict(extra="forbid")

    points: Annotated[list[Point], Field(min_length=2)]


class Region(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    country: str
    coverage: RegionCoverage

    @field_validator("name")
    @classmethod
    def name_non_empty_after_strip(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("name must be non-empty after strip")
        return stripped

    @field_validator("country")
    @classmethod
    def country_iso_alpha2(cls, value: str) -> str:
        if len(value) != 2 or not value.isalpha() or value != value.upper():
            raise ValueError("country must be ISO 3166-1 alpha-2 (two uppercase letters)")
        return value


class Route(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    route_type: RouteType
    region: Region
    publication: Publication
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
    duration_is_estimated: bool
    original_difficulty_value: str | None = None
    original_difficulty_scale: str | None = None
    difficulty: "Difficulty | None" = None
    closure_assessment: "ClosureAssessment | None" = None
    season_months: set[int]
    season_note: str | None = None
    description: str
    transit_accessibility: TransitAccessibility
    official_source_links: list[str]
    provenance: Provenance
    completeness: Completeness
    assessment: Assessment

    @field_validator("name")
    @classmethod
    def name_non_empty_after_strip(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("name must be non-empty after strip")
        return stripped

    @field_validator("linestring", mode="before")
    @classmethod
    def coerce_linestring(cls, value: object) -> object:
        if value is None or isinstance(value, LineString):
            return value
        if isinstance(value, list):
            return {"points": value}
        return value

    @field_validator("gpx")
    @classmethod
    def gpx_not_empty_string(cls, value: str | None) -> str | None:
        if value == "":
            raise ValueError("gpx must be None or a non-empty string")
        return value

    @field_validator("season_months")
    @classmethod
    def season_months_in_range(cls, value: set[int]) -> set[int]:
        if any(month < 1 or month > 12 for month in value):
            raise ValueError("season_months values must be integers from 1 to 12")
        return value

    @field_validator("official_source_links")
    @classmethod
    def official_source_links_are_http_urls(cls, value: list[str]) -> list[str]:
        for item in value:
            _HTTP_URL.validate_python(item)
        return value

    @model_validator(mode="after")
    def check_route_invariants(self) -> Self:
        if (
            self.elevation_min_m is not None
            and self.elevation_max_m is not None
            and self.elevation_max_m < self.elevation_min_m
        ):
            raise ValueError("elevation_max_m must be greater than or equal to elevation_min_m")

        value_set = self.original_difficulty_value is not None
        scale_set = self.original_difficulty_scale is not None
        if value_set != scale_set:
            raise ValueError(
                "original_difficulty_value and original_difficulty_scale must both be set or both be None"
            )

        if self.publication == Publication.PUBLISHED:
            if self.trailhead is None:
                raise ValueError("trailhead is required when publication is published")
            if self.linestring is None:
                raise ValueError("linestring is required when publication is published")
            if self.elevation_min_m is None:
                raise ValueError("elevation_min_m is required when publication is published")
            if self.elevation_max_m is None:
                raise ValueError("elevation_max_m is required when publication is published")
            if self.duration_minutes is None:
                raise ValueError("duration_minutes is required when publication is published")

        if (
            self.route_type == RouteType.KLETTERSTEIG
            and self.publication != Publication.QUARANTINED
        ):
            missing = [
                name
                for name, minutes in (
                    ("approach_minutes", self.approach_minutes),
                    ("technical_minutes", self.technical_minutes),
                    ("descent_minutes", self.descent_minutes),
                )
                if minutes is None
            ]
            if missing:
                raise ValueError(
                    "Klettersteig publication other than quarantined requires "
                    + ", ".join(missing)
                )

        if (
            self.duration_minutes is not None
            and self.approach_minutes is not None
            and self.technical_minutes is not None
            and self.descent_minutes is not None
            and self.duration_minutes
            != self.approach_minutes + self.technical_minutes + self.descent_minutes
        ):
            raise ValueError(
                "duration_minutes must equal approach_minutes + technical_minutes + descent_minutes"
            )

        if self.difficulty is not None:
            if self.difficulty.route_type != self.route_type:
                raise ValueError("difficulty.route_type must equal route_type")
            if self.difficulty.original_value != self.original_difficulty_value:
                raise ValueError(
                    "difficulty.original_value must equal original_difficulty_value"
                )
            if self.difficulty.original_scale != self.original_difficulty_scale:
                raise ValueError(
                    "difficulty.original_scale must equal original_difficulty_scale"
                )
            originals_missing = (
                self.original_difficulty_value is None
                and self.original_difficulty_scale is None
            )
            if originals_missing and (
                self.difficulty.structured_value is not None
                or self.difficulty.mapped_huebler is not None
            ):
                raise ValueError(
                    "mapped difficulty is rejected when original difficulty strings are both None"
                )

        return self


from app.domain.closure import ClosureAssessment as ClosureAssessment

try:
    from app.domain.difficulty import Difficulty as Difficulty
except ImportError:
    pass
else:
    Route.model_rebuild()
