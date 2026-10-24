import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func
from sqlalchemy import select

from app.data.seed_routes import PUBLISHED_ALPINE_HIKE_SLUG
from app.data.seed_routes import seed_route_id
from app.db import create_sessionmaker
from app.models.route_revision import RouteRevisionRecord
from app.repositories.routes import current_applied_revision_number
from app.repositories.routes import list_route_revisions
from tests.test_route_search import _operator_url


def _current_base(migrated_test_database: str, route_id) -> int:
    Session = create_sessionmaker(_operator_url(migrated_test_database))
    with Session() as session:
        current = current_applied_revision_number(session, route_id)
    assert current is not None
    return current


pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL is unset",
)

pytest_plugins = ["tests.test_route_search"]


def _pending_count(migrated_test_database: str, route_id) -> int:
    Session = create_sessionmaker(_operator_url(migrated_test_database))
    with Session() as session:
        return (
            session.scalar(
                select(func.count())
                .select_from(RouteRevisionRecord)
                .where(
                    RouteRevisionRecord.route_id == route_id,
                    RouteRevisionRecord.application_status == "pending",
                )
            )
            or 0
        )


def test_pending_revision_leaves_get_detail_unchanged(
    seeded_client: TestClient,
    migrated_test_database: str,
) -> None:
    route_id = seed_route_id(PUBLISHED_ALPINE_HIKE_SLUG)
    before = seeded_client.get(f"/routes/{route_id}").json()
    base = _current_base(migrated_test_database, route_id)
    response = seeded_client.post(
        f"/routes/{route_id}/protected-edits",
        json={"base_revision_number": base, "name": "Pending rename only"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["application_status"] == "pending"
    assert body["revision_number"] >= 1

    after = seeded_client.get(f"/routes/{route_id}").json()
    assert after == before

    Session = create_sessionmaker(_operator_url(migrated_test_database))
    with Session() as session:
        revisions = list_route_revisions(session, route_id)
    pending = [rev for rev in revisions if rev.application_status == "pending"]
    assert len(pending) == 1
    assert pending[0].before_snapshot is not None
    assert pending[0].before_snapshot["name"] == before["name"]
    assert pending[0].after_snapshot["name"] == "Pending rename only"


def test_validation_error_does_not_create_pending_row(
    seeded_client: TestClient,
    migrated_test_database: str,
) -> None:
    route_id = seed_route_id(PUBLISHED_ALPINE_HIKE_SLUG)
    before_count = _pending_count(migrated_test_database, route_id)
    base = _current_base(migrated_test_database, route_id)
    response = seeded_client.post(
        f"/routes/{route_id}/protected-edits",
        json={
            "base_revision_number": base,
            "elevation_max_m": 100,
            "elevation_min_m": 5000,
        },
    )
    assert response.status_code == 422
    assert _pending_count(migrated_test_database, route_id) == before_count
