from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.domain.route import Route
from app.domain.route import RouteType
from app.planning.closure_input import PlanClosureInput
from app.planning.thunderstorm import ThunderstormAssessment
from app.planning.thunderstorm import ThunderstormRisk
from app.planning.versions import PLANNING_RULES_VERSION
from app.planning.weather import WeatherAssessment
from app.planning.weather import WeatherFreshness


class Recommendation(StrEnum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"
    UNKNOWN = "unknown"


class Confidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class RecommendationResult:
    recommendation: Recommendation
    confidence: Confidence
    rules_version: str
    explanation: list[str]
    critical_gaps: list[str]


def judge_recommendation(
    route: Route,
    *,
    weather: WeatherAssessment,
    closure: PlanClosureInput,
    thunderstorm: ThunderstormAssessment,
    daylight_calculable: bool,
) -> RecommendationResult:
    explanation: list[str] = []
    critical_gaps: list[str] = []

    if closure.hard_blocker:
        explanation.append("Active closure assessment blocks the plan.")
        return RecommendationResult(
            recommendation=Recommendation.RED,
            confidence=Confidence.HIGH,
            rules_version=PLANNING_RULES_VERSION,
            explanation=explanation,
            critical_gaps=["closure_active"],
        )

    if closure.planning_value == "unknown":
        critical_gaps.append("closure_unknown")
        explanation.append("Closure assessment is missing, unreviewed, or expired.")

    if weather.freshness is WeatherFreshness.STALE:
        critical_gaps.append("weather_stale")
        explanation.append("Weather forecast is stale.")
    elif weather.freshness is WeatherFreshness.UNKNOWN or weather.forecast is None:
        critical_gaps.append("weather_missing")
        explanation.append("Weather forecast unavailable.")

    if thunderstorm.risk is ThunderstormRisk.HIGH:
        explanation.append("Thunderstorm heuristic is high.")
        return RecommendationResult(
            recommendation=Recommendation.RED,
            confidence=Confidence.MEDIUM,
            rules_version=PLANNING_RULES_VERSION,
            explanation=explanation,
            critical_gaps=critical_gaps,
        )

    if critical_gaps:
        return RecommendationResult(
            recommendation=Recommendation.UNKNOWN,
            confidence=Confidence.LOW,
            rules_version=PLANNING_RULES_VERSION,
            explanation=explanation,
            critical_gaps=critical_gaps,
        )

    if thunderstorm.risk is ThunderstormRisk.MODERATE:
        explanation.append("Thunderstorm heuristic is moderate.")
        rec = Recommendation.YELLOW
    elif not daylight_calculable:
        explanation.append("Daylight window could not be fully assessed.")
        rec = Recommendation.YELLOW
    else:
        explanation.append("Critical inputs present and fresh.")
        rec = Recommendation.GREEN

    if route.route_type is RouteType.OUTDOOR_CLIMBING:
        explanation.append(
            "Climbing plan does not assess technical route suitability or protection."
        )

    confidence = Confidence.HIGH if rec is Recommendation.GREEN else Confidence.MEDIUM
    return RecommendationResult(
        recommendation=rec,
        confidence=confidence,
        rules_version=PLANNING_RULES_VERSION,
        explanation=explanation,
        critical_gaps=critical_gaps,
    )
