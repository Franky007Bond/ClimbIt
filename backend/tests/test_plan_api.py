import os
import uuid
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.data.seed_routes import PUBLISHED_ALPINE_HIKE_SLUG
from app.data.seed_routes import seed_route_id
from app.planning.transit import ComponentStatus
from app.planning.transit import TransitSummary
from app.planning.versions import TRANSITOUS_ADAPTER_VERSION
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
    body = response.json()
    assert body["components"]["transit"]["status"] == "degraded"
    assert body["components"]["transit"]["live_available"] is False
    assert body["components"]["transit"]["journey_planner_url"] is None
    assert body["recommendation"] != "green"


def test_missed_last_return_yields_red_recommendation(
    seeded_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _MissedReturnPort:
        adapter_version = TRANSITOUS_ADAPTER_VERSION

        def plan_transit(self, **_kwargs: object) -> TransitSummary:
            query_time = _kwargs.get("query_time")
            assert isinstance(query_time, datetime)
            return TransitSummary(
                status=ComponentStatus.OK,
                adapter_version=self.adapter_version,
                summary="Synthetic ok outbound with missed return.",
                origin_region="DE-BY",
                last_return_feasible=False,
                source_time=query_time,
            )

    monkeypatch.setattr(
        "app.planning.service.get_transit_port",
        lambda: _MissedReturnPort(),
    )
    route_id = seed_route_id(PUBLISHED_ALPINE_HIKE_SLUG)
    response = seeded_client.post(
        f"/routes/{route_id}/plans",
        json={"plan_date": "2026-07-15", "origin": "munich"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["recommendation"] == "red"
    assert body["components"]["transit"]["last_return_feasible"] is False
    assert body["components"]["transit"]["live_available"] is True
    assert body["transit_summary"] == "Synthetic ok outbound with missed return."
    joined = " ".join(body["explanation"]).lower()
    assert "return connection" in joined


def test_plan_response_transit_matches_persisted_run(
    seeded_client: TestClient, migrated_test_database: str
) -> None:
    route_id = seed_route_id(PUBLISHED_ALPINE_HIKE_SLUG)
    response = seeded_client.post(
        f"/routes/{route_id}/plans",
        json={"plan_date": "2026-07-15", "origin": "Munich Hauptbahnhof"},
    )
    assert response.status_code == 200
    body = response.json()
    run_id = body["plan_run_id"]
    Session = create_sessionmaker(_operator_url(migrated_test_database))
    with Session() as session:
        stored = get_plan_run(session, uuid.UUID(run_id))
    assert stored is not None
    assert body["transit_summary"] == stored.result.get("transit_summary")
    assert body["origin_region"] == stored.result.get("origin_region")
    assert stored.source_timestamps.get("transit") is not None
    assert (
        body["components"]["transit"]["live_available"]
        == stored.result["components"]["transit"]["live_available"]
    )
    assert (
        body["components"]["transit"]["journey_planner_url"]
        == stored.result["components"]["transit"]["journey_planner_url"]
    )
