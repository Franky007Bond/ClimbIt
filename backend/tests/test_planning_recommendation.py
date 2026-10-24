from dataclasses import replace
from datetime import datetime
from datetime import timezone

from app.data.seed_routes import build_seed_routes
from app.domain.route import RouteType
from app.planning.avalanche import AvalancheAssessmentKind
from app.planning.avalanche import AvalancheFreshness
from app.planning.avalanche import AvalanchePlanningInput
from app.planning.closure_input import PlanClosureInput
from app.planning.recommendation import Confidence
from app.planning.recommendation import Recommendation
from app.planning.recommendation import judge_recommendation
from app.planning.thunderstorm import ThunderstormAssessment
from app.planning.thunderstorm import ThunderstormRisk
from app.planning.thunderstorm import assess_thunderstorm_risk
from app.planning.versions import THUNDERSTORM_HEURISTIC_VERSION
from app.planning.weather import WeatherAssessment
from app.planning.weather import WeatherFreshness
from app.planning.weather import WeatherForecast


def _assessed_avalanche(**overrides: object) -> AvalanchePlanningInput:
    base = AvalanchePlanningInput(
        freshness=AvalancheFreshness.OK,
        assessment=AvalancheAssessmentKind.ASSESSED,
        region_key="at-tyrol",
        region_label="Tyrol (Austria)",
        official_bulletin_url="https://example.invalid/at",
        bulletin=None,
        adapter_version="mock-avalanche-1",
    )
    return replace(base, **overrides) if overrides else base


def _climbing_route():
    return next(
        route for _id, route in build_seed_routes() if route.route_type is RouteType.OUTDOOR_CLIMBING
    )


def test_missing_closure_cannot_be_green() -> None:
    route = _climbing_route()
    weather = WeatherAssessment(
        freshness=WeatherFreshness.OK,
        forecast=WeatherForecast(
            temperature_c=10,
            wind_ms=2,
            precipitation_mm=0,
            freezing_level_m=3000,
            cape_j_kg=100,
            precip_probability=10,
            source_time=datetime.now(timezone.utc),
        ),
        adapter_version="mock",
    )
    closure = PlanClosureInput(planning_value="unknown", source_timestamp=None, hard_blocker=False)
    thunder = assess_thunderstorm_risk(weather.forecast, exposure="moderate", start_hour_local=8)
    result = judge_recommendation(
        route,
        weather=weather,
        avalanche=_assessed_avalanche(),
        closure=closure,
        thunderstorm=thunder,
        daylight_calculable=True,
    )
    assert result.recommendation is not Recommendation.GREEN


def test_stale_weather_cannot_be_green() -> None:
    route = _climbing_route()
    weather = WeatherAssessment(
        freshness=WeatherFreshness.STALE,
        forecast=None,
        adapter_version="mock",
    )
    closure = PlanClosureInput(
        planning_value="none_known",
        source_timestamp=datetime.now(timezone.utc),
        hard_blocker=False,
    )
    thunder = ThunderstormAssessment(
        risk=ThunderstormRisk.LOW,
        heuristic_version=THUNDERSTORM_HEURISTIC_VERSION,
        label="heuristic",
        factors=[],
    )
    result = judge_recommendation(
        route,
        weather=weather,
        avalanche=_assessed_avalanche(),
        closure=closure,
        thunderstorm=thunder,
        daylight_calculable=True,
    )
    assert result.recommendation is not Recommendation.GREEN


def test_stale_avalanche_cannot_be_green() -> None:
    route = _climbing_route()
    weather = WeatherAssessment(
        freshness=WeatherFreshness.OK,
        forecast=WeatherForecast(
            temperature_c=10,
            wind_ms=2,
            precipitation_mm=0,
            freezing_level_m=3000,
            cape_j_kg=50,
            precip_probability=5,
            source_time=datetime.now(timezone.utc),
        ),
        adapter_version="mock",
    )
    closure = PlanClosureInput(
        planning_value="none_known",
        source_timestamp=datetime.now(timezone.utc),
        hard_blocker=False,
    )
    thunder = ThunderstormAssessment(
        risk=ThunderstormRisk.LOW,
        heuristic_version=THUNDERSTORM_HEURISTIC_VERSION,
        label="heuristic",
        factors=[],
    )
    avalanche = _assessed_avalanche(
        freshness=AvalancheFreshness.STALE,
        assessment=AvalancheAssessmentKind.UNKNOWN,
    )
    result = judge_recommendation(
        route,
        weather=weather,
        avalanche=avalanche,
        closure=closure,
        thunderstorm=thunder,
        daylight_calculable=True,
    )
    assert result.recommendation is not Recommendation.GREEN
    assert "avalanche_stale" in result.critical_gaps


def test_climbing_plan_explanation_mentions_no_technical_suitability() -> None:
    route = _climbing_route()
    weather = WeatherAssessment(
        freshness=WeatherFreshness.OK,
        forecast=WeatherForecast(
            temperature_c=10,
            wind_ms=2,
            precipitation_mm=0,
            freezing_level_m=3000,
            cape_j_kg=50,
            precip_probability=5,
            source_time=datetime.now(timezone.utc),
        ),
        adapter_version="mock",
    )
    closure = PlanClosureInput(
        planning_value="none_known",
        source_timestamp=datetime.now(timezone.utc),
        hard_blocker=False,
    )
    thunder = assess_thunderstorm_risk(weather.forecast, exposure="moderate", start_hour_local=8)
    result = judge_recommendation(
        route,
        weather=weather,
        avalanche=_assessed_avalanche(),
        closure=closure,
        thunderstorm=thunder,
        daylight_calculable=True,
    )
    joined = " ".join(result.explanation).lower()
    assert "technical" in joined
    assert result.confidence is not Confidence.UNKNOWN
