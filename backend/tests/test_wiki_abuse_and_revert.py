import json
import os

import bcrypt
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

TEST_USERNAME = "operator"
TEST_PASSWORD = "test-password"
TEST_HASH = bcrypt.hashpw(
    TEST_PASSWORD.encode("utf-8"), bcrypt.gensalt(rounds=4)
).decode()


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


def test_rate_limit_blocks_excess_descriptive_edits(
    seeded_client: TestClient,
    migrated_test_database: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WIKI_ANONYMOUS_EDIT_RATE_LIMIT_MAX", "3")
    monkeypatch.setenv("WIKI_ANONYMOUS_EDIT_RATE_LIMIT_WINDOW_SECONDS", "3600")
    route_id = seed_route_id(PUBLISHED_ALPINE_HIKE_SLUG)
    base = _current_base(migrated_test_database, route_id)
    for index in range(3):
        response = seeded_client.patch(
            f"/routes/{route_id}/descriptive",
            json={
                "base_revision_number": base + index,
                "description": f"Edit {index}",
            },
        )
        assert response.status_code == 200
    blocked = seeded_client.patch(
        f"/routes/{route_id}/descriptive",
        json={"base_revision_number": base + 3, "description": "Too many"},
    )
    assert blocked.status_code == 429
    assert blocked.headers.get("Retry-After") is not None


def test_approved_revert_restores_prior_description(
    seeded_client: TestClient,
    migrated_test_database: str,
) -> None:
    route_id = seed_route_id(PUBLISHED_ALPINE_HIKE_SLUG)
    base = _current_base(migrated_test_database, route_id)
    original = seeded_client.get(f"/routes/{route_id}").json()["description"]
    seeded_client.patch(
        f"/routes/{route_id}/descriptive",
        json={"base_revision_number": base, "description": "Changed description"},
    )
    Session = create_sessionmaker(_operator_url(migrated_test_database))
    with Session() as session:
        from app.models.route_revision import RouteRevisionRecord
        from sqlalchemy import select

        anchor = session.scalar(
            select(RouteRevisionRecord.id).where(
                RouteRevisionRecord.route_id == route_id
            )
        )
    assert anchor is not None
    _login(seeded_client)
    revert = seeded_client.post(f"/maintainer/revisions/{anchor}/revert", json={})
    assert revert.status_code == 201
    pending_id = revert.json()["revision_id"]
    approve = seeded_client.post(f"/maintainer/revisions/{pending_id}/approve")
    assert approve.status_code == 204
    restored = seeded_client.get(f"/routes/{route_id}").json()["description"]
    assert restored == original
