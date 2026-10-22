from __future__ import annotations

import uuid
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.domain.difficulty import Difficulty
from app.domain.route import Assessment
from app.domain.route import Completeness
from app.domain.route import Provenance
from app.domain.route import Publication
from app.domain.route import Region
from app.domain.route import RouteType
from app.domain.route import TransitAccessibility


class RouteSearchItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    name: str
    route_type: RouteType
    region: Region
    publication: Publication
    provenance: Provenance
    completeness: Completeness
    assessment: Assessment
    duration_minutes: int | None
    duration_is_estimated: bool
    transit_accessibility: TransitAccessibility
    season_months: list[int]
    difficulty: Difficulty | None


class RouteSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    routes: list[RouteSearchItem]


PositiveMinutesQuery = Annotated[int, Field(gt=0)]
SeasonMonthQuery = Annotated[int, Field(ge=1, le=12)]
