from __future__ import annotations

import os
from collections import Counter

import pytest

pytest_plugins = ("test_route_search",)
from fastapi.testclient import TestClient

from app.data.seed_routes import FRENCH_SWISS_LAUNCH_SLUGS
from app.data.seed_routes import PUBLISHED_ALPINE_HIKE_SLUG
from app.data.seed_routes import SEED_FIXTURE_SLUGS
from app.data.seed_routes import build_seed_routes
from app.data.seed_routes import seed_route_id
from app.data.seed_routes_french_swiss import FRENCH_SWISS_CATALOG_SLUGS
from app.data.seed_routes_french_swiss import FRENCH_SWISS_LAUNCH_PUBLISHED_COUNT
from app.domain.route import Publication
from app.domain.route import RegionCoverage
from app.domain.route import RouteType

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL is unset",
)

SAMPLE_LAT_MIN = 45.85
SAMPLE_LAT_MAX = 46.60
SAMPLE_LON_MIN = 6.85
SAMPLE_LON_MAX = 8.35

FRENCH_SWISS_ROUTE_TYPE_COUNTS = {
    RouteType.KLETTERSTEIG: 2,
    RouteType.ALPINE_HIKE: 2,
    RouteType.OUTDOOR_CLIMBING: 1,
}

_KLETTERSTEIG_ORIGINAL_SCALES = frozenset({"huebler", "Huebler", "Hübler", "k1_k6"})


def test_french_swiss_launch_slug_inventory() -> None:
    assert len(FRENCH_SWISS_CATALOG_SLUGS) == 4
    assert len(FRENCH_SWISS_LAUNCH_SLUGS) == FRENCH_SWISS_LAUNCH_PUBLISHED_COUNT
    assert FRENCH_SWISS_LAUNCH_PUBLISHED_COUNT == 5
    assert FRENCH_SWISS_LAUNCH_SLUGS[0] == PUBLISHED_ALPINE_HIKE_SLUG
    assert set(FRENCH_SWISS_CATALOG_SLUGS).isdisjoint(set(SEED_FIXTURE_SLUGS))


def test_build_seed_routes_french_swiss_launch_invariants() -> None:
    fixtures = dict(build_seed_routes())
    launch = [fixtures[seed_route_id(slug)] for slug in FRENCH_SWISS_LAUNCH_SLUGS]
    assert len(launch) == FRENCH_SWISS_LAUNCH_PUBLISHED_COUNT

    type_counts = Counter(route.route_type for route in launch)
    for route_type, expected in FRENCH_SWISS_ROUTE_TYPE_COUNTS.items():
        assert type_counts[route_type] == expected

    for route in launch:
        assert route.publication is Publication.PUBLISHED
        assert route.region.coverage is RegionCoverage.SAMPLE
        assert route.region.country in {"FR", "CH"}
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
        assert "Seed Published" not in route.name
        for point in route.linestring.points:
            assert SAMPLE_LAT_MIN <= point.latitude <= SAMPLE_LAT_MAX
            assert SAMPLE_LON_MIN <= point.longitude <= SAMPLE_LON_MAX
        if route.route_type is RouteType.KLETTERSTEIG:
            assert route.approach_minutes is not None
            assert route.technical_minutes is not None
            assert route.descent_minutes is not None
            assert route.duration_minutes == (
                route.approach_minutes + route.technical_minutes + route.descent_minutes
            )


def test_french_swiss_hiking_and_klettersteig_scales_differ() -> None:
    fixtures = dict(build_seed_routes())
    launch = [fixtures[seed_route_id(slug)] for slug in FRENCH_SWISS_LAUNCH_SLUGS]
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


def test_search_region_filter_returns_sample_coverage(
    seeded_client: TestClient,
) -> None:
    for region_name in ("Chamonix", "Zermatt", "Grimsel"):
        response = seeded_client.get("/routes", params={"region": region_name})
        assert response.status_code == 200
        routes = response.json()["routes"]
        assert routes
        for item in routes:
            assert item["region"]["coverage"] == "sample"
            assert item["region"]["name"] == region_name
            assert item["publication"] == "published"


def test_search_lists_five_sample_routes_by_coverage(seeded_client: TestClient) -> None:
    response = seeded_client.get("/routes")
    assert response.status_code == 200
    sample_routes = [
        item
        for item in response.json()["routes"]
        if item["region"]["coverage"] == "sample"
    ]
    assert len(sample_routes) == FRENCH_SWISS_LAUNCH_PUBLISHED_COUNT
