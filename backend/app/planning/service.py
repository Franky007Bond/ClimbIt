from __future__ import annotations

import uuid
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timezone
from typing import Any

from sqlalchemy.orm import Session

from app.domain.plan_run import PlanRun
from app.domain.route import Route
from app.planning.closure_input import build_plan_closure_input
from app.planning.daylight import calculate_daylight_window
from app.planning.daylight import trailhead_timezone
from app.planning.gear import build_gear_guidance
from app.planning.recommendation import judge_recommendation
from app.planning.thunderstorm import assess_thunderstorm_risk
from app.planning.transit import ComponentStatus
from app.planning.transit import mock_transit_summary
from app.planning.versions import DEFAULT_DIFFICULTY_MAPPING_VERSION
from app.planning.versions import PLANNING_RULES_VERSION
from app.planning.weather import CachedWeatherBoundary
from app.planning.weather import MockWeatherAdapter
from app.planning.weather import WeatherAssessment
from app.planning.weather import WeatherFreshness
from app.planning.weather import assess_weather_freshness
from app.repositories.plan_runs import create_plan_run
from app.repositories.plan_runs import new_plan_run_id
from app.repositories.plan_runs import plan_run_created_at

SAFETY_DISCLAIMER = (
    "ClimbIt provides planning assistance, not authorization to undertake a route. "
    "Local conditions, official warnings, and your judgment remain authoritative."
)


def _weather_component_status(freshness: WeatherFreshness) -> ComponentStatus:
    if freshness is WeatherFreshness.OK:
        return ComponentStatus.OK
    if freshness is WeatherFreshness.STALE:
        return ComponentStatus.DEGRADED
    return ComponentStatus.UNKNOWN


def build_plan(
    session: Session,
    *,
    route: Route,
    route_id: uuid.UUID,
    plan_date: date,
    origin: str,
    start_time_local: time | None,
    now: datetime | None = None,
) -> tuple[PlanRun, dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    plan_date_str = plan_date.isoformat()
    weather_port = CachedWeatherBoundary(MockWeatherAdapter())
    forecast = None
    freshness = WeatherFreshness.UNKNOWN
    if route.elevation_min_m is not None and route.elevation_max_m is not None:
        forecast = weather_port.fetch_forecast(
            route_id=route_id,
            plan_date=plan_date_str,
            elevation_min_m=route.elevation_min_m,
            elevation_max_m=route.elevation_max_m,
        )
        freshness = assess_weather_freshness(forecast, now)
    weather = WeatherAssessment(
        freshness=freshness,
        forecast=forecast,
        adapter_version=weather_port.adapter_version,
    )
    closure = build_plan_closure_input(route, now)
    start_hour = start_time_local.hour if start_time_local else None
    thunderstorm = assess_thunderstorm_risk(
        forecast if freshness is WeatherFreshness.OK else None,
        exposure="high" if route.route_type.value == "klettersteig" else "moderate",
        start_hour_local=start_hour,
    )
    daylight = calculate_daylight_window(route, plan_date, start_time_local=start_time_local)
    daylight_calculable = daylight.latest_safe_start_local is not None
    recommendation = judge_recommendation(
        route,
        weather=weather,
        closure=closure,
        thunderstorm=thunderstorm,
        daylight_calculable=daylight_calculable,
    )
    gear = build_gear_guidance(route, forecast if freshness is WeatherFreshness.OK else None)
    transit = mock_transit_summary(origin)

    response_payload: dict[str, Any] = {
        "plan_run_id": None,
        "route_id": str(route_id),
        "plan_date": plan_date_str,
        "trailhead_timezone": trailhead_timezone(route),
        "safety_disclaimer": SAFETY_DISCLAIMER,
        "recommendation": recommendation.recommendation.value,
        "confidence": recommendation.confidence.value,
        "components": {
            "weather": {
                "status": _weather_component_status(freshness).value,
                "freshness": freshness.value,
            },
            "closure": {
                "status": ComponentStatus.OK.value
                if closure.planning_value != "unknown"
                else ComponentStatus.UNKNOWN.value,
                "planning_value": closure.planning_value,
            },
            "transit": {
                "status": transit.status.value,
                "summary": transit.summary,
                "last_return_feasible": transit.last_return_feasible,
            },
            "thunderstorm": {
                "status": ComponentStatus.OK.value,
                "risk": thunderstorm.risk.value,
                "label": thunderstorm.label,
            },
            "gear": {"status": ComponentStatus.OK.value},
            "daylight": {
                "status": ComponentStatus.OK.value
                if daylight_calculable
                else ComponentStatus.UNKNOWN.value,
            },
        },
        "weather": None
        if forecast is None
        else {
            "temperature_c": forecast.temperature_c,
            "wind_ms": forecast.wind_ms,
            "precipitation_mm": forecast.precipitation_mm,
            "freezing_level_m": forecast.freezing_level_m,
            "source_time": forecast.source_time.isoformat(),
        },
        "gear": [{"name": item.name, "reason": item.reason} for item in gear.items],
        "daylight": {
            "latest_safe_start_local": daylight.latest_safe_start_local.isoformat()
            if daylight.latest_safe_start_local
            else None,
            "be_off_by_local": daylight.be_off_by_local.isoformat()
            if daylight.be_off_by_local
            else None,
            "explanation": daylight.explanation,
        },
        "explanation": recommendation.explanation + daylight.explanation,
        "thunderstorm": {
            "risk": thunderstorm.risk.value,
            "factors": thunderstorm.factors,
            "label": thunderstorm.label,
            "heuristic_version": thunderstorm.heuristic_version,
        },
    }

    mapping_version = (
        route.difficulty.mapping_version
        if route.difficulty is not None
        else DEFAULT_DIFFICULTY_MAPPING_VERSION
    )
    stored_input = {
        "route_id": str(route_id),
        "plan_date": plan_date_str,
        "start_time_local": start_time_local.isoformat() if start_time_local else None,
        "trailhead_timezone": trailhead_timezone(route),
    }
    source_timestamps = {
        "weather": forecast.source_time if forecast is not None else None,
        "closure": closure.source_timestamp,
    }
    stored_result = {
        **response_payload,
        "transit_summary": transit.summary,
        "origin_region": transit.origin_region,
    }
    stored_result.pop("plan_run_id", None)

    run = PlanRun(
        id=new_plan_run_id(),
        route_id=route_id,
        created_at=plan_run_created_at(),
        input_snapshot=stored_input,
        source_timestamps=source_timestamps,
        rules_version=PLANNING_RULES_VERSION,
        mapping_version=mapping_version,
        adapter_versions={
            "weather": weather_port.adapter_version,
            "transit": transit.adapter_version,
        },
        explanation=list(recommendation.explanation),
        result=stored_result,
    )
    create_plan_run(session, run)
    session.flush()
    response_payload["plan_run_id"] = str(run.id)
    return run, response_payload
