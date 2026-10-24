from __future__ import annotations

import os
from collections import Counter

import pytest

pytest_plugins = ("test_route_search",)
from fastapi.testclient import TestClient

from app.data.seed_routes import ALLGAEU
from app.data.seed_routes import ALLGAEU_LAUNCH_SLUGS
from app.data.seed_routes import SEED_FIXTURE_SLUGS
from app.data.seed_routes import build_seed_routes
from app.data.seed_routes import seed_route_id
from app.data.seed_routes_allgaeu import ALLGAEU_CATALOG_SLUGS
from app.data.seed_routes_allgaeu import ALLGAEU_LAUNCH_PUBLISHED_COUNT
from app.domain.route import Publication
from app.domain.route import RouteType
pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL is unset",
)


def test_allgaeu_launch_slug_inventory() -> None:
    assert len(ALLGAEU_CATALOG_SLUGS) == 18
    assert len(ALLGAEU_LAUNCH_SLUGS) == ALLGAEU_LAUNCH_PUBLISHED_COUNT
    assert ALLGAEU_LAUNCH_PUBLISHED_COUNT == 20
    assert set(ALLGAEU_LAUNCH_SLUGS).isdisjoint(
        set(SEED_FIXTURE_SLUGS) - {
            "published-klettersteig",
            "published-outdoor-climbing",
        }
    )


def test_build_seed_routes_allgaeu_launch_invariants() -> None:
    fixtures = dict(build_seed_routes())
    launch = [
        fixtures[seed_route_id(slug)]
        for slug in ALLGAEU_LAUNCH_SLUGS
    ]
    assert len(launch) == ALLGAEU_LAUNCH_PUBLISHED_COUNT

    type_counts = Counter(route.route_type for route in launch)
    for route_type in (
        RouteType.KLETTERSTEIG,
        RouteType.ALPINE_HIKE,
        RouteType.OUTDOOR_CLIMBING,
    ):
        assert type_counts[route_type] >= 2

    for route in launch:
        assert route.publication is Publication.PUBLISHED
        assert route.region == ALLGAEU
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
            assert 47.0 <= point.latitude <= 47.65
            assert 10.0 <= point.longitude <= 10.65
        if route.route_type is RouteType.KLETTERSTEIG:
            assert route.approach_minutes is not None
            assert route.technical_minutes is not None
            assert route.descent_minutes is not None
            assert route.duration_minutes == (
                route.approach_minutes
                + route.technical_minutes
                + route.descent_minutes
            )


def test_search_lists_twenty_allgaeu_routes(seeded_client: TestClient) -> None:
    response = seeded_client.get("/routes", params={"region": "Allgäu"})
    assert response.status_code == 200
    routes = response.json()["routes"]
    assert len(routes) == ALLGAEU_LAUNCH_PUBLISHED_COUNT
    for item in routes:
        assert item["region"]["coverage"] == "supported"
        assert item["region"]["name"] == "Allgäu"
        assert item["region"]["country"] == "DE"
        assert item["publication"] == "published"


def test_search_allgaeu_route_type_counts(seeded_client: TestClient) -> None:
    for route_type, expected in (
        ("klettersteig", 6),
        ("alpine_hike", 7),
        ("outdoor_climbing", 7),
    ):
        response = seeded_client.get(
            "/routes",
            params={"region": "Allgäu", "route_type": route_type},
        )
        assert response.status_code == 200
        assert len(response.json()["routes"]) == expected
