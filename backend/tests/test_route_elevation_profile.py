from app.data.seed_routes import PUBLISHED_ALPINE_HIKE_SLUG
from app.data.seed_routes import build_seed_routes
from app.data.seed_routes import seed_route_id
from app.domain.route import LineString
from app.domain.route import Point
from app.routes.elevation_profile import ELEVATION_PROFILE_MAX_POINTS
from app.routes.elevation_profile import build_elevation_profile
from app.routes.trailhead_transit import resolve_trailhead_transit_connection


def _published_alpine_hike():
    target = seed_route_id(PUBLISHED_ALPINE_HIKE_SLUG)
    return next(r for rid, r in build_seed_routes() if rid == target)


def _westliche_karwendelspitze():
    target = seed_route_id("tyrol-westliche-karwendelspitze")
    return next(r for rid, r in build_seed_routes() if rid == target)


def test_seed_route_has_elevation_profile_with_distance_axis() -> None:
    route = _published_alpine_hike()
    profile = build_elevation_profile(route)
    assert profile is not None
    assert profile.synthesized is True
    assert len(profile.points) >= 2
    assert profile.points[0].distance_m == 0
    assert profile.points[-1].distance_m > profile.points[0].distance_m
    elevations = [point.elevation_m for point in profile.points]
    assert min(elevations) >= route.elevation_min_m
    assert max(elevations) <= route.elevation_max_m


def test_westliche_karwendelspitze_uses_gpx_elevations() -> None:
    route = _westliche_karwendelspitze()
    assert route.gpx is not None
    profile = build_elevation_profile(route)
    assert profile is not None
    assert profile.synthesized is False
    assert len(profile.points) >= 2
    assert len(profile.points) <= ELEVATION_PROFILE_MAX_POINTS

    elevations = [point.elevation_m for point in profile.points]
    assert max(elevations) > 2300


def test_gpx_profile_differs_from_synthesized_fallback() -> None:
    route = _westliche_karwendelspitze()
    gpx_profile = build_elevation_profile(route)
    sine_profile = build_elevation_profile(route.model_copy(update={"gpx": None}))
    assert gpx_profile is not None
    assert sine_profile is not None
    assert gpx_profile.synthesized is False
    assert sine_profile.synthesized is True
    assert gpx_profile.points[-1].elevation_m != sine_profile.points[-1].elevation_m


def test_profile_null_without_elevation() -> None:
    route = _published_alpine_hike().model_copy(update={"elevation_min_m": None})
    assert build_elevation_profile(route) is None


def test_chamonix_sample_resolves_nearby_transit_hub() -> None:
    route = _published_alpine_hike()
    connection = resolve_trailhead_transit_connection(route)
    assert connection is not None
    assert connection.hub_id == "fr-chamonix"
    assert connection.distance_m <= 35_000


def test_distant_trailhead_has_no_transit_connection() -> None:
    route = _published_alpine_hike().model_copy(
        update={
            "trailhead": Point(latitude=0.0, longitude=0.0),
            "linestring": LineString(
                points=[
                    Point(latitude=0.0, longitude=0.0),
                    Point(latitude=0.01, longitude=0.01),
                ]
            ),
        }
    )
    assert resolve_trailhead_transit_connection(route) is None
