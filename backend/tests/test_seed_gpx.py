from __future__ import annotations

from app.data.seed_gpx import load_seed_gpx
from app.data.seed_gpx import seed_gpx_geometry
from app.data.seed_routes import build_seed_routes
from app.data.seed_routes import seed_route_id
from app.routes.trailhead_transit import resolve_trailhead_transit_connection


def test_westliche_karwendelspitze_seed_route_uses_full_gpx_track() -> None:
    fixtures = dict(build_seed_routes())
    route = fixtures[seed_route_id("tyrol-westliche-karwendelspitze")]
    assert route.linestring is not None
    assert len(route.linestring.points) == 2032
    assert route.gpx is not None
    assert route.trailhead == route.linestring.points[0]
    assert route.name == "Westliche Karwendelspitze"
    assert route.official_source_links == [
        "https://www.hoehenrausch.de/berge/westliche-karwendelspitze/",
    ]


def test_westliche_karwendelspitze_nearest_transit_is_mittenwald_bahnhof() -> None:
    fixtures = dict(build_seed_routes())
    route = fixtures[seed_route_id("tyrol-westliche-karwendelspitze")]
    connection = resolve_trailhead_transit_connection(route)
    assert connection is not None
    assert connection.hub_id == "de-mittenwald-bahnhof"
    assert connection.stop_name == "Mittenwald Bahnhof"
    assert connection.distance_m < 500


def test_load_westliche_karwendelspitze_gpx() -> None:
    processed = load_seed_gpx("westliche_karwendelspitze.gpx")
    assert len(processed.linestring.points) == 2032
    assert processed.elevation_min_m is not None
    assert processed.elevation_max_m is not None

    trailhead, linestring, gpx = seed_gpx_geometry("westliche_karwendelspitze.gpx")
    assert trailhead == linestring.points[0]
    assert len(linestring.points) == 2032
    assert gpx.startswith("<?xml")
