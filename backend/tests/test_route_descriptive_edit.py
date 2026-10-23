import os

import pytest
from fastapi.testclient import TestClient

from app.data.seed_routes import PUBLISHED_ALPINE_HIKE_SLUG
from app.data.seed_routes import QUARANTINED_ALPINE_HIKE_SLUG
from app.data.seed_routes import seed_route_id
from app.db import create_sessionmaker
from app.repositories.routes import current_applied_revision_number
from tests.test_route_search import _operator_url

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL is unset",
)

pytest_plugins = ["tests.test_route_search"]


def _current_base(migrated_test_database: str, route_id) -> int:
    Session = create_sessionmaker(_operator_url(migrated_test_database))
    with Session() as session:
        current = current_applied_revision_number(session, route_id)
    assert current is not None
    return current


def test_description_update_round_trips_on_get_detail(
    seeded_client: TestClient,
    migrated_test_database: str,
) -> None:
    route_id = seed_route_id(PUBLISHED_ALPINE_HIKE_SLUG)
    base = _current_base(migrated_test_database, route_id)
    before = seeded_client.get(f"/routes/{route_id}").json()
    patch = seeded_client.patch(
        f"/routes/{route_id}/descriptive",
        json={
            "base_revision_number": base,
            "description": "Updated alpine description for tests.",
        },
    )
    assert patch.status_code == 200
    body = patch.json()
    assert body["description"] == "Updated alpine description for tests."
    assert isinstance(body["revision_number"], int)
    assert body["revision_number"] >= 1

    after = seeded_client.get(f"/routes/{route_id}").json()
    assert after["description"] == "Updated alpine description for tests."
    assert after["name"] == before["name"]
    assert after["route_type"] == before["route_type"]
    assert after["trailhead"] == before["trailhead"]
    assert after["linestring"] == before["linestring"]
    assert after["region"] == before["region"]
    assert after["publication"] == before["publication"]


def test_season_note_only_update(
    seeded_client: TestClient,
    migrated_test_database: str,
) -> None:
    route_id = seed_route_id(PUBLISHED_ALPINE_HIKE_SLUG)
    base = _current_base(migrated_test_database, route_id)
    before = seeded_client.get(f"/routes/{route_id}").json()
    response = seeded_client.patch(
        f"/routes/{route_id}/descriptive",
        json={"base_revision_number": base, "season_note": "Best in stable weather."},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["season_note"] == "Best in stable weather."
    assert body["description"] == before["description"]
    detail = seeded_client.get(f"/routes/{route_id}").json()
    assert detail["season_note"] == "Best in stable weather."


def test_quarantined_route_returns_404(
    seeded_client: TestClient,
    migrated_test_database: str,
) -> None:
    route_id = seed_route_id(QUARANTINED_ALPINE_HIKE_SLUG)
    base = _current_base(migrated_test_database, route_id)
    response = seeded_client.patch(
        f"/routes/{route_id}/descriptive",
        json={"base_revision_number": base, "description": "Should not apply."},
    )
    assert response.status_code == 404


def test_both_fields_omitted_returns_422(seeded_client: TestClient) -> None:
    route_id = seed_route_id(PUBLISHED_ALPINE_HIKE_SLUG)
    response = seeded_client.patch(f"/routes/{route_id}/descriptive", json={})
    assert response.status_code == 422


def test_no_maintainer_session_required(
    seeded_client: TestClient,
    migrated_test_database: str,
) -> None:
    route_id = seed_route_id(PUBLISHED_ALPINE_HIKE_SLUG)
    base = _current_base(migrated_test_database, route_id)
    response = seeded_client.patch(
        f"/routes/{route_id}/descriptive",
        json={"base_revision_number": base, "description": "Anonymous wiki fix."},
    )
    assert response.status_code == 200
    assert response.json()["description"] == "Anonymous wiki fix."
