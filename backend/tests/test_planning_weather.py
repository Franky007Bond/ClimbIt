from dataclasses import replace
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from uuid import uuid4

from app.planning.weather import CachedWeatherBoundary
from app.planning.weather import MockWeatherAdapter
from app.planning.weather import WeatherFreshness
from app.planning.weather import assess_weather_freshness


def test_stale_forecast_becomes_stale() -> None:
    forecast = MockWeatherAdapter().fetch_forecast(
        route_id=uuid4(),
        plan_date="2026-07-15",
        elevation_min_m=1000,
        elevation_max_m=2000,
    )
    old = datetime.now(timezone.utc) - timedelta(hours=7)
    stale_forecast = replace(forecast, source_time=old, max_age_seconds=6 * 3600)
    assert (
        assess_weather_freshness(stale_forecast, datetime.now(timezone.utc))
        is WeatherFreshness.STALE
    )


def test_mock_weather_can_be_substituted_via_cache_boundary() -> None:
    inner = MockWeatherAdapter()
    cached = CachedWeatherBoundary(inner)
    kwargs = {
        "route_id": uuid4(),
        "plan_date": "2026-07-15",
        "elevation_min_m": 1000,
        "elevation_max_m": 2000,
    }
    first = cached.fetch_forecast(**kwargs)
    second = cached.fetch_forecast(**kwargs)
    assert first is second
    assert cached.adapter_version == inner.adapter_version
