from datetime import date

from app.data.seed_routes import PUBLISHED_ALPINE_HIKE_SLUG
from app.data.seed_routes import build_seed_routes
from app.data.seed_routes import seed_route_id
from app.planning.daylight import calculate_daylight_window


def test_calculable_summer_day_returns_times() -> None:
    target_id = seed_route_id(PUBLISHED_ALPINE_HIKE_SLUG)
    route = next(
        route for route_id, route in build_seed_routes() if route_id == target_id
    )
    route = route.model_copy(update={"duration_is_estimated": False})
    window = calculate_daylight_window(route, date(2026, 7, 15))
    assert window.latest_safe_start_local is not None
    assert window.be_off_by_local is not None


def test_estimated_duration_leaves_times_unset() -> None:
    target_id = seed_route_id(PUBLISHED_ALPINE_HIKE_SLUG)
    route = next(
        route for route_id, route in build_seed_routes() if route_id == target_id
    )
    estimated = route.model_copy(update={"duration_is_estimated": True})
    window = calculate_daylight_window(estimated, date(2026, 7, 15))
    assert window.latest_safe_start_local is None
    assert window.be_off_by_local is None
    assert any("estimated" in line.lower() for line in window.explanation)
