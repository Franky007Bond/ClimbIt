from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CreateTripRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_run_id: str = Field(min_length=1)


class TripListItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trip_id: str
    route_id: str
    latest_plan_run_id: str
    plan_date: str
    recommendation: str
    last_change_summary: dict[str, Any] | None


class TripListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trips: list[TripListItem]


class TripDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trip_id: str
    route_id: str
    latest_plan_run_id: str
    plan_date: str
    recommendation: str
    confidence: str
    last_change_summary: dict[str, Any] | None
    components: dict[str, Any]
    explanation: list[str]


class CreateShareLinkResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    share_token: str


class SharedPlanSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_run_id: str
    route_id: str
    plan_date: str
    recommendation: str
    confidence: str
    components: dict[str, Any]
    explanation: list[str]
    origin_region: str | None
