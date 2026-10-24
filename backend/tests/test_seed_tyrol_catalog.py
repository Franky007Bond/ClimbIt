from __future__ import annotations

import os
from collections import Counter

import pytest

pytest_plugins = ("test_route_search",)
from fastapi.testclient import TestClient

from app.data.seed_routes import SEED_FIXTURE_SLUGS
from app.data.seed_routes import TYROL
from app.data.seed_routes import TYROL_LAUNCH_SLUGS
from app.data.seed_routes import build_seed_routes
from app.data.seed_routes import seed_route_id
from app.data.seed_routes_tyrol import TYROL_CATALOG_SLUGS
from app.data.seed_routes_tyrol import TYROL_LAUNCH_PUBLISHED_COUNT
from app.domain.route import Publication
from app.domain.route import RouteType

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL is unset",
)

TYROL_LAT_MIN = 46.85
TYROL_LAT_MAX = 47.55
TYROL_LON_MIN = 10.85
TYROL_LON_MAX = 12.40

TYROL_ROUTE_TYPE_COUNTS = {
    RouteType.KLETTERSTEIG: 5,
    RouteType.ALPINE_HIKE: 5,
    RouteType.OUTDOOR_CLIMBING: 5,
}


def test_tyrol_launch_slug_inventory() -> None:
    assert len(TYROL_CATALOG_SLUGS) == 15
    assert len(TYROL_LAUNCH_SLUGS) == TYROL_LAUNCH_PUBLISHED_COUNT
    assert TYROL_LAUNCH_PUBLISHED_COUNT == 15
    assert set(TYROL_LAUNCH_SLUGS).isdisjoint(set(SEED_FIXTURE_SLUGS))


def test_build_seed_routes_tyrol_launch_invariants() -> None:
    fixtures = dict(build_seed_routes())
    launch = [
        fixtures[seed_route_id(slug)]
        for slug in TYROL_LAUNCH_SLUGS
    ]
    assert len(launch) == TYROL_LAUNCH_PUBLISHED_COUNT

    type_counts = Counter(route.route_type for route in launch)
    for route_type, expected in TYROL_ROUTE_TYPE_COUNTS.items():
        assert type_counts[route_type] == expected
        assert type_counts[route_type] >= 2

    for route in launch:
        assert route.publication is Publication.PUBLISHED
        assert route.region == TYROL
        assert route.completeness.value == "complete"
        assert route.description.strip()
        assert route.season_months
        assert route.official_source_links
        assert route.trailhead is not None
        assert route.linestring is not None
        assert len(route.linestring.points) >= 2
        assert route.elevation_min_m is not None
        assert route.elevation_max_m is not None
        assert route.duration_minutes is not None
        assert route.duration_is_estimated is True
        assert route.difficulty is not None
        for point in route.linestring.points:
            assert TYROL_LAT_MIN <= point.latitude <= TYROL_LAT_MAX
            assert TYROL_LON_MIN <= point.longitude <= TYROL_LON_MAX
        if route.route_type is RouteType.KLETTERSTEIG:
            assert route.approach_minutes is not None
            assert route.technical_minutes is not None
            assert route.descent_minutes is not None
            assert route.duration_minutes == (
                route.approach_minutes
                + route.technical_minutes
                + route.descent_minutes
            )


def test_search_lists_fifteen_tyrol_routes(seeded_client: TestClient) -> None:
    response = seeded_client.get("/routes", params={"region": "Tyrol"})
    assert response.status_code == 200
    routes = response.json()["routes"]
    assert len(routes) == TYROL_LAUNCH_PUBLISHED_COUNT
    for item in routes:
        assert item["region"]["coverage"] == "supported"
        assert item["region"]["name"] == "Tyrol"
        assert item["region"]["country"] == "AT"
        assert item["publication"] == "published"


def test_search_tyrol_route_type_counts(seeded_client: TestClient) -> None:
    for route_type, expected in (
        ("klettersteig", 5),
        ("alpine_hike", 5),
        ("outdoor_climbing", 5),
    ):
        response = seeded_client.get(
            "/routes",
            params={"region": "Tyrol", "route_type": route_type},
        )
        assert response.status_code == 200
        assert len(response.json()["routes"]) == expected
