from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from app.planning.versions import MOCK_WEATHER_ADAPTER_VERSION
from app.planning.versions import WEATHER_MAX_AGE_SECONDS


class WeatherFreshness(StrEnum):
    OK = "ok"
    STALE = "stale"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class WeatherForecast:
    temperature_c: float
    wind_ms: float
    precipitation_mm: float
    freezing_level_m: int
    cape_j_kg: float
    precip_probability: float
    source_time: datetime
    max_age_seconds: int = WEATHER_MAX_AGE_SECONDS


@dataclass(frozen=True, slots=True)
class WeatherAssessment:
    freshness: WeatherFreshness
    forecast: WeatherForecast | None
    adapter_version: str


class WeatherPort(Protocol):
    adapter_version: str

    def fetch_forecast(
        self,
        *,
        route_id: UUID,
        plan_date: str,
        elevation_min_m: int,
        elevation_max_m: int,
    ) -> WeatherForecast: ...


def assess_weather_freshness(forecast: WeatherForecast, now: datetime) -> WeatherFreshness:
    if now.tzinfo is None or now.utcoffset() != timedelta(0):
        raise ValueError("now must be UTC-aware")
    age = (now - forecast.source_time).total_seconds()
    if age > forecast.max_age_seconds:
        return WeatherFreshness.STALE
    return WeatherFreshness.OK


class MockWeatherAdapter:
    adapter_version = MOCK_WEATHER_ADAPTER_VERSION

    def fetch_forecast(
        self,
        *,
        route_id: UUID,
        plan_date: str,
        elevation_min_m: int,
        elevation_max_m: int,
    ) -> WeatherForecast:
        del elevation_min_m, elevation_max_m
        # Deterministic but varied mock keyed by route and date.
        key = hash((str(route_id), plan_date)) % 1000
        return WeatherForecast(
            temperature_c=8.0 + (key % 10),
            wind_ms=3.0 + (key % 5),
            precipitation_mm=float(key % 3),
            freezing_level_m=3200 + (key % 200),
            cape_j_kg=float(200 + (key % 800)),
            precip_probability=float(10 + (key % 70)),
            source_time=datetime.now(timezone.utc),
        )


class CachedWeatherBoundary:
    """Cache boundary wrapper; stores last fetch per route/date key."""

    def __init__(self, inner: WeatherPort) -> None:
        self._inner = inner
        self._cache: dict[tuple[str, str], WeatherForecast] = {}

    @property
    def adapter_version(self) -> str:
        return self._inner.adapter_version

    def fetch_forecast(
        self,
        *,
        route_id: UUID,
        plan_date: str,
        elevation_min_m: int,
        elevation_max_m: int,
    ) -> WeatherForecast:
        cache_key = (str(route_id), plan_date)
        if cache_key not in self._cache:
            self._cache[cache_key] = self._inner.fetch_forecast(
                route_id=route_id,
                plan_date=plan_date,
                elevation_min_m=elevation_min_m,
                elevation_max_m=elevation_max_m,
            )
        return self._cache[cache_key]
