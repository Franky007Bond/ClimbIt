from __future__ import annotations

from datetime import date
from datetime import time
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_date: date
    origin: str = Field(min_length=1)
    start_time_local: time | None = None


class PlanResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_run_id: str
    trace_id: str | None
    route_id: str
    plan_date: str
    trailhead_timezone: str
    safety_disclaimer: str
    recommendation: str
    confidence: str
    components: dict[str, Any]
    weather: dict[str, Any] | None
    gear: list[dict[str, str]]
    daylight: dict[str, Any]
    explanation: list[str]
    thunderstorm: dict[str, Any]
    avalanche: dict[str, Any] | None
    transit_summary: str
    origin_region: str | None
