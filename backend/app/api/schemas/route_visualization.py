from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ElevationProfilePoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    distance_m: float = Field(ge=0)
    elevation_m: int


class ElevationProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    points: list[ElevationProfilePoint]
    synthesized: bool = True


class TrailheadTransitConnection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hub_id: str = Field(min_length=1)
    stop_name: str = Field(min_length=1)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    distance_m: float = Field(ge=0)
