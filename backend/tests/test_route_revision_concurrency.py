import json
import os

import pytest
from fastapi.testclient import TestClient

from app.data.seed_routes import PUBLISHED_ALPINE_HIKE_SLUG
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


def test_stale_descriptive_edit_returns_409(
    seeded_client: TestClient,
    migrated_test_database: str,
) -> None:
    route_id = seed_route_id(PUBLISHED_ALPINE_HIKE_SLUG)
    base = _current_base(migrated_test_database, route_id)
    first = seeded_client.patch(
        f"/routes/{route_id}/descriptive",
        json={"base_revision_number": base, "description": "First edit"},
    )
    assert first.status_code == 200
    stale = seeded_client.patch(
        f"/routes/{route_id}/descriptive",
        json={"base_revision_number": base, "description": "Stale edit"},
    )
    assert stale.status_code == 409
    body = stale.json()["detail"]
    assert body["code"] == "revision_conflict"
    assert body["current_base_revision_number"] == first.json()["revision_number"]


def test_stale_protected_edit_after_descriptive_bump_returns_409(
    seeded_client: TestClient,
    migrated_test_database: str,
) -> None:
    route_id = seed_route_id(PUBLISHED_ALPINE_HIKE_SLUG)
    base = _current_base(migrated_test_database, route_id)
    pending_a = seeded_client.post(
        f"/routes/{route_id}/protected-edits",
        json={"base_revision_number": base, "name": "Pending A"},
    )
    assert pending_a.status_code == 201
    bump = seeded_client.patch(
        f"/routes/{route_id}/descriptive",
        json={"base_revision_number": base, "description": "Bump applied head"},
    )
    assert bump.status_code == 200
    stale = seeded_client.post(
        f"/routes/{route_id}/protected-edits",
        json={"base_revision_number": base, "name": "Pending B"},
    )
    assert stale.status_code == 409
