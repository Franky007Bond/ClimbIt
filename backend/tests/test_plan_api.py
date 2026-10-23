import os
import uuid

import pytest
from fastapi.testclient import TestClient

from app.data.seed_routes import PUBLISHED_ALPINE_HIKE_SLUG
from app.data.seed_routes import seed_route_id
from app.repositories.plan_runs import get_plan_run
from app.db import create_sessionmaker
from tests.test_route_search import _operator_url

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL is unset",
)

pytest_plugins = ["tests.test_route_search"]


def test_plan_endpoint_persists_run_without_exact_origin(
    seeded_client: TestClient, migrated_test_database: str
) -> None:
    route_id = seed_route_id(PUBLISHED_ALPINE_HIKE_SLUG)
    response = seeded_client.post(
        f"/routes/{route_id}/plans",
        json={
            "plan_date": "2026-07-15",
            "origin": "Munich Hauptbahnhof platform 11",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["recommendation"] in {"green", "yellow", "red", "unknown"}
    assert body["components"]["transit"]["status"] in {"ok", "degraded", "unknown"}
    run_id = body["plan_run_id"]
    Session = create_sessionmaker(_operator_url(migrated_test_database))
    with Session() as session:
        stored = get_plan_run(session, uuid.UUID(run_id))
    assert stored is not None
    assert "origin" not in stored.input_snapshot
    assert "Munich" not in str(stored.result)
    assert stored.result.get("origin_region") is not None


def test_unavailable_transit_component_is_degraded(seeded_client: TestClient) -> None:
    route_id = seed_route_id(PUBLISHED_ALPINE_HIKE_SLUG)
    response = seeded_client.post(
        f"/routes/{route_id}/plans",
        json={"plan_date": "2026-07-15", "origin": "unknown"},
    )
    assert response.status_code == 200
    assert response.json()["components"]["transit"]["status"] == "degraded"
