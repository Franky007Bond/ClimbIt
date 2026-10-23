import json
import os
import uuid

import bcrypt
import pytest
from fastapi.testclient import TestClient

from app.data.seed_routes import PUBLISHED_ALPINE_HIKE_SLUG
from app.data.seed_routes import seed_route_id
from app.db import create_sessionmaker
from app.main import app
from app.repositories.routes import current_applied_revision_number
from tests.test_route_search import _operator_url

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL is unset",
)

pytest_plugins = ["tests.test_route_search"]

TEST_USERNAME = "operator"
TEST_PASSWORD = "test-password"
TEST_HASH = bcrypt.hashpw(TEST_PASSWORD.encode("utf-8"), bcrypt.gensalt(rounds=4)).decode()


@pytest.fixture(autouse=True)
def maintainer_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAINTAINER_SESSION_SECRET", "test-maintainer-secret")
    monkeypatch.setenv(
        "MAINTAINER_ALLOWLIST",
        json.dumps([{"username": TEST_USERNAME, "password_bcrypt": TEST_HASH}]),
    )


def _current_base(migrated_test_database: str, route_id) -> int:
    Session = create_sessionmaker(_operator_url(migrated_test_database))
    with Session() as session:
        current = current_applied_revision_number(session, route_id)
    assert current is not None
    return current


def _login(client: TestClient) -> None:
    response = client.post(
        "/maintainer/sessions",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200


def test_anonymous_approve_returns_401(seeded_client: TestClient) -> None:
    response = seeded_client.post(f"/maintainer/revisions/{uuid.uuid4()}/approve")
    assert response.status_code == 401


def test_reject_leaves_published_route_unchanged(
    seeded_client: TestClient,
    migrated_test_database: str,
) -> None:
    route_id = seed_route_id(PUBLISHED_ALPINE_HIKE_SLUG)
    before = seeded_client.get(f"/routes/{route_id}").json()
    base = _current_base(migrated_test_database, route_id)
    pending = seeded_client.post(
        f"/routes/{route_id}/protected-edits",
        json={"base_revision_number": base, "name": "Rejected pending name"},
    )
    assert pending.status_code == 201
    revision_id = pending.json()["revision_id"]
    _login(seeded_client)
    reject = seeded_client.post(f"/maintainer/revisions/{revision_id}/reject")
    assert reject.status_code == 204
    after = seeded_client.get(f"/routes/{route_id}").json()
    assert after == before


def test_approve_updates_get_detail(
    seeded_client: TestClient,
    migrated_test_database: str,
) -> None:
    route_id = seed_route_id(PUBLISHED_ALPINE_HIKE_SLUG)
    base = _current_base(migrated_test_database, route_id)
    pending = seeded_client.post(
        f"/routes/{route_id}/protected-edits",
        json={"base_revision_number": base, "name": "Approved pending name"},
    )
    assert pending.status_code == 201
    revision_id = pending.json()["revision_id"]
    _login(seeded_client)
    approve = seeded_client.post(f"/maintainer/revisions/{revision_id}/approve")
    assert approve.status_code == 204
    detail = seeded_client.get(f"/routes/{route_id}").json()
    assert detail["name"] == "Approved pending name"


def test_diff_includes_changed_field(
    seeded_client: TestClient,
    migrated_test_database: str,
) -> None:
    route_id = seed_route_id(PUBLISHED_ALPINE_HIKE_SLUG)
    base = _current_base(migrated_test_database, route_id)
    pending = seeded_client.post(
        f"/routes/{route_id}/protected-edits",
        json={"base_revision_number": base, "name": "Diff pending name"},
    )
    revision_id = pending.json()["revision_id"]
    _login(seeded_client)
    detail = seeded_client.get(f"/maintainer/revisions/{revision_id}")
    assert detail.status_code == 200
    fields = {item["field"] for item in detail.json()["field_diffs"]}
    assert "name" in fields
