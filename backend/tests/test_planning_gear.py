from app.data.seed_routes import build_seed_routes
from app.domain.route import RouteType
from app.planning.gear import build_gear_guidance
from app.planning.weather import MockWeatherAdapter
from uuid import uuid4


def test_climbing_gear_does_not_recommend_technical_protection() -> None:
    climbing = next(
        route for _id, route in build_seed_routes() if route.route_type is RouteType.OUTDOOR_CLIMBING
    )
    forecast = MockWeatherAdapter().fetch_forecast(
        route_id=uuid4(),
        plan_date="2026-07-15",
        elevation_min_m=1000,
        elevation_max_m=1500,
    )
    guidance = build_gear_guidance(climbing, forecast)
    names = " ".join(item.name.lower() for item in guidance.items)
    assert "via ferrata" not in names
    assert "harness" not in names
    assert "protection" not in names
