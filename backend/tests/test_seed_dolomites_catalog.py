from __future__ import annotations

import os
from collections import Counter

import pytest

pytest_plugins = ("test_route_search",)
from fastapi.testclient import TestClient

from app.data.seed_routes import DOLOMITES
from app.data.seed_routes import DOLOMITES_LAUNCH_SLUGS
from app.data.seed_routes import SEED_FIXTURE_SLUGS
from app.data.seed_routes import build_seed_routes
from app.data.seed_routes import seed_route_id
from app.data.seed_routes_dolomites import DOLOMITES_CATALOG_SLUGS
from app.data.seed_routes_dolomites import DOLOMITES_LAUNCH_PUBLISHED_COUNT
from app.domain.route import Publication
from app.domain.route import RouteType

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL is unset",
)

DOLOMITES_LAT_MIN = 46.15
DOLOMITES_LAT_MAX = 46.75
DOLOMITES_LON_MIN = 11.52
DOLOMITES_LON_MAX = 12.35

DOLOMITES_ROUTE_TYPE_COUNTS = {
    RouteType.KLETTERSTEIG: 4,
    RouteType.ALPINE_HIKE: 3,
    RouteType.OUTDOOR_CLIMBING: 3,
}

_KLETTERSTEIG_ORIGINAL_SCALES = frozenset({"huebler", "Huebler", "Hübler", "k1_k6"})


def test_dolomites_launch_slug_inventory() -> None:
    assert len(DOLOMITES_CATALOG_SLUGS) == 10
    assert len(DOLOMITES_LAUNCH_SLUGS) == DOLOMITES_LAUNCH_PUBLISHED_COUNT
    assert DOLOMITES_LAUNCH_PUBLISHED_COUNT == 10
    assert set(DOLOMITES_LAUNCH_SLUGS).isdisjoint(set(SEED_FIXTURE_SLUGS))


def test_build_seed_routes_dolomites_launch_invariants() -> None:
    fixtures = dict(build_seed_routes())
    launch = [
        fixtures[seed_route_id(slug)]
        for slug in DOLOMITES_LAUNCH_SLUGS
    ]
    assert len(launch) == DOLOMITES_LAUNCH_PUBLISHED_COUNT

    type_counts = Counter(route.route_type for route in launch)
    for route_type, expected in DOLOMITES_ROUTE_TYPE_COUNTS.items():
        assert type_counts[route_type] == expected
        assert type_counts[route_type] >= 2

    for route in launch:
        assert route.publication is Publication.PUBLISHED
        assert route.region == DOLOMITES
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
            assert DOLOMITES_LAT_MIN <= point.latitude <= DOLOMITES_LAT_MAX
            assert DOLOMITES_LON_MIN <= point.longitude <= DOLOMITES_LON_MAX
        if route.route_type is RouteType.KLETTERSTEIG:
            assert route.approach_minutes is not None
            assert route.technical_minutes is not None
            assert route.descent_minutes is not None
            assert route.duration_minutes == (
                route.approach_minutes
                + route.technical_minutes
                + route.descent_minutes
            )


def test_dolomites_hiking_and_klettersteig_scales_differ() -> None:
    fixtures = dict(build_seed_routes())
    launch = [
        fixtures[seed_route_id(slug)]
        for slug in DOLOMITES_LAUNCH_SLUGS
    ]
    hike_scales = {
        route.original_difficulty_scale
        for route in launch
        if route.route_type is RouteType.ALPINE_HIKE
    }
    klettersteig_scales = {
        route.original_difficulty_scale
        for route in launch
        if route.route_type is RouteType.KLETTERSTEIG
    }
    assert hike_scales == {"SAC"}
    assert klettersteig_scales & _KLETTERSTEIG_ORIGINAL_SCALES
    assert hike_scales.isdisjoint(klettersteig_scales)


def test_search_lists_ten_dolomites_routes(seeded_client: TestClient) -> None:
    response = seeded_client.get("/routes", params={"region": "Dolomites"})
    assert response.status_code == 200
    routes = response.json()["routes"]
    assert len(routes) == DOLOMITES_LAUNCH_PUBLISHED_COUNT
    for item in routes:
        assert item["region"]["coverage"] == "supported"
        assert item["region"]["name"] == "Dolomites"
        assert item["region"]["country"] == "IT"
        assert item["publication"] == "published"


def test_search_dolomites_route_type_counts(seeded_client: TestClient) -> None:
    for route_type, expected in (
        ("klettersteig", 4),
        ("alpine_hike", 3),
        ("outdoor_climbing", 3),
    ):
        response = seeded_client.get(
            "/routes",
            params={"region": "Dolomites", "route_type": route_type},
        )
        assert response.status_code == 200
        assert len(response.json()["routes"]) == expected
