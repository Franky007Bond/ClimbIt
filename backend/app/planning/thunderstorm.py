from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.planning.versions import THUNDERSTORM_HEURISTIC_VERSION
from app.planning.weather import WeatherForecast


class ThunderstormRisk(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ThunderstormAssessment:
    risk: ThunderstormRisk
    heuristic_version: str
    label: str
    factors: list[str]


# Thresholds live in versioned configuration for this heuristic release.
_CAPE_HIGH = 800.0
_CAPE_MODERATE = 400.0
_PRECIP_PROB_HIGH = 60.0
_PRECIP_PROB_MODERATE = 35.0
_AFTERNOON_HOUR_START = 12


def assess_thunderstorm_risk(
    forecast: WeatherForecast | None,
    *,
    exposure: str,
    start_hour_local: int | None,
) -> ThunderstormAssessment:
    label = "Thunderstorm risk is a heuristic, not a forecast guarantee."
    if forecast is None:
        return ThunderstormAssessment(
            risk=ThunderstormRisk.UNKNOWN,
            heuristic_version=THUNDERSTORM_HEURISTIC_VERSION,
            label=label,
            factors=["weather_forecast_missing"],
        )
    factors: list[str] = []
    score = 0
    if forecast.cape_j_kg >= _CAPE_HIGH:
        score += 2
        factors.append("cape_high")
    elif forecast.cape_j_kg >= _CAPE_MODERATE:
        score += 1
        factors.append("cape_moderate")
    if forecast.precip_probability >= _PRECIP_PROB_HIGH:
        score += 2
        factors.append("precip_probability_high")
    elif forecast.precip_probability >= _PRECIP_PROB_MODERATE:
        score += 1
        factors.append("precip_probability_moderate")
    if exposure == "high":
        score += 1
        factors.append("high_exposure")
    if start_hour_local is not None and start_hour_local >= _AFTERNOON_HOUR_START:
        score += 1
        factors.append("afternoon_start")
    if score >= 4:
        risk = ThunderstormRisk.HIGH
    elif score >= 2:
        risk = ThunderstormRisk.MODERATE
    else:
        risk = ThunderstormRisk.LOW
    return ThunderstormAssessment(
        risk=risk,
        heuristic_version=THUNDERSTORM_HEURISTIC_VERSION,
        label=label,
        factors=factors,
    )
