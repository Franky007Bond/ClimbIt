import os
import uuid

import pytest
from fastapi.testclient import TestClient

from app.data.seed_routes import PUBLISHED_ALPINE_HIKE_SLUG
from app.data.seed_routes import PUBLISHED_KLETTERSTEIG_SLUG
from app.data.seed_routes import QUARANTINED_ALPINE_HIKE_SLUG
from app.data.seed_routes import QUARANTINED_KLETTERSTEIG_SLUG
from app.data.seed_routes import QUARANTINED_OUTDOOR_CLIMBING_SLUG
from app.data.seed_routes import seed_route_id

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL is unset",
)

pytest_plugins = ["tests.test_route_search"]


def test_published_route_returns_detail_with_geometry(
    seeded_client: TestClient,
) -> None:
    route_id = seed_route_id(PUBLISHED_ALPINE_HIKE_SLUG)
    response = seeded_client.get(f"/routes/{route_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(route_id)
    assert body["publication"] == "published"
    assert body["provenance"] == "seed"
    assert body["completeness"] == "complete"
    assert body["assessment"] == "unassessed"
    assert body["region"]["name"] == "Chamonix"
    assert body["region"]["country"] == "FR"
    assert body["region"]["coverage"] == "sample"
    trailhead = body["trailhead"]
    assert trailhead is not None
    assert "longitude" in trailhead and "latitude" in trailhead
    linestring = body["linestring"]
    assert linestring is not None
    assert len(linestring["points"]) >= 2
    for point in linestring["points"]:
        assert "longitude" in point and "latitude" in point
    assert body["gpx"] is None
    assert body["closure_assessment"] is None


def test_unknown_route_id_returns_404(seeded_client: TestClient) -> None:
    response = seeded_client.get(f"/routes/{uuid.uuid4()}")
    assert response.status_code == 404


@pytest.mark.parametrize(
    "slug",
    [
        QUARANTINED_KLETTERSTEIG_SLUG,
        QUARANTINED_ALPINE_HIKE_SLUG,
        QUARANTINED_OUTDOOR_CLIMBING_SLUG,
    ],
)
def test_quarantined_route_id_returns_404(seeded_client: TestClient, slug: str) -> None:
    response = seeded_client.get(f"/routes/{seed_route_id(slug)}")
    assert response.status_code == 404


def test_invalid_route_id_returns_422(seeded_client: TestClient) -> None:
    response = seeded_client.get("/routes/not-a-uuid")
    assert response.status_code == 422


def test_published_klettersteig_duration_is_estimated(
    seeded_client: TestClient,
) -> None:
    route_id = seed_route_id(PUBLISHED_KLETTERSTEIG_SLUG)
    response = seeded_client.get(f"/routes/{route_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["duration_is_estimated"] is True
    assert body["approach_minutes"] is not None
    assert body["technical_minutes"] is not None
    assert body["descent_minutes"] is not None
