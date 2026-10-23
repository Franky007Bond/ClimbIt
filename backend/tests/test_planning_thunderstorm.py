from datetime import datetime
from datetime import timezone

from app.planning.thunderstorm import ThunderstormRisk
from app.planning.thunderstorm import assess_thunderstorm_risk
from app.planning.weather import WeatherForecast


def _forecast(**overrides: object) -> WeatherForecast:
    base = {
        "temperature_c": 10.0,
        "wind_ms": 3.0,
        "precipitation_mm": 0.0,
        "freezing_level_m": 3000,
        "cape_j_kg": 100.0,
        "precip_probability": 10.0,
        "source_time": datetime.now(timezone.utc),
    }
    base.update(overrides)
    return WeatherForecast(**base)  # type: ignore[arg-type]


def test_thunderstorm_low_risk_case() -> None:
    result = assess_thunderstorm_risk(
        _forecast(cape_j_kg=100, precip_probability=10),
        exposure="moderate",
        start_hour_local=8,
    )
    assert result.risk is ThunderstormRisk.LOW
    assert "heuristic" in result.label.lower()


def test_thunderstorm_high_risk_case() -> None:
    result = assess_thunderstorm_risk(
        _forecast(cape_j_kg=900, precip_probability=80),
        exposure="high",
        start_hour_local=14,
    )
    assert result.risk is ThunderstormRisk.HIGH


def test_thunderstorm_missing_forecast_is_unknown() -> None:
    result = assess_thunderstorm_risk(None, exposure="high", start_hour_local=10)
    assert result.risk is ThunderstormRisk.UNKNOWN
