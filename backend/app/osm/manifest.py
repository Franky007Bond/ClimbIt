from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.domain.route import PositiveMinutes, RouteType


class OsmElementType(StrEnum):
    WAY = "way"
    RELATION = "relation"


class ManifestEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    osm_type: OsmElementType
    osm_id: Annotated[int, Field(gt=0)]
    name: str
    route_type: RouteType
    region_name: str
    region_country: str
    duration_minutes: PositiveMinutes | None = None


class ImportManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entries: Annotated[list[ManifestEntry], Field(min_length=1)]


def load_manifest(path: str) -> ImportManifest:
    import json
    from pathlib import Path

    raw = Path(path).read_text(encoding="utf-8")
    data = json.loads(raw)
    return ImportManifest.model_validate(data)
