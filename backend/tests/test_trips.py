import json
import os
import uuid
from datetime import datetime
from datetime import timedelta
from datetime import timezone

import pytest
from fastapi.testclient import TestClient

from app.data.seed_routes import PUBLISHED_ALPINE_HIKE_SLUG
from app.data.seed_routes import seed_route_id
from app.db import create_sessionmaker
from app.main import app
from app.models.trip import TripRecord
from app.repositories.plan_runs import get_plan_run
from tests.test_route_search import _operator_url

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL is unset",
)

pytest_plugins = ["tests.test_route_search", "tests.test_trip_capability"]


def _create_plan(client: TestClient) -> str:
    route_id = seed_route_id(PUBLISHED_ALPINE_HIKE_SLUG)
    response = client.post(
        f"/routes/{route_id}/plans",
        json={"plan_date": "2026-07-15", "origin": "Munich region"},
    )
    assert response.status_code == 200
    return response.json()["plan_run_id"]


def _save_trip(client: TestClient, plan_run_id: str) -> str:
    client.get("/trips/capability")
    created = client.post("/trips", json={"plan_run_id": plan_run_id})
    assert created.status_code == 201
    return created.json()["trip_id"]


def test_save_and_list_trips_for_capability(seeded_client: TestClient) -> None:
    plan_run_id = _create_plan(seeded_client)
    trip_id = _save_trip(seeded_client, plan_run_id)
    listed = seeded_client.get("/trips")
    assert listed.status_code == 200
    trips = listed.json()["trips"]
    assert len(trips) == 1
    assert trips[0]["trip_id"] == trip_id
    assert trips[0]["latest_plan_run_id"] == plan_run_id
    assert "email" not in json.dumps(trips[0]).lower()
    assert "profile" not in json.dumps(trips[0]).lower()


def test_other_capability_cannot_read_trip(seeded_client: TestClient) -> None:
    plan_run_id = _create_plan(seeded_client)
    trip_id = _save_trip(seeded_client, plan_run_id)
    other = TestClient(app)
    other.get("/trips/capability")
    detail = other.get(f"/trips/{trip_id}")
    assert detail.status_code == 404


def test_reevaluate_keeps_old_run_and_records_changes(
    seeded_client: TestClient,
    migrated_test_database: str,
) -> None:
    plan_run_id = _create_plan(seeded_client)
    trip_id = _save_trip(seeded_client, plan_run_id)
    Session = create_sessionmaker(_operator_url(migrated_test_database))
    with Session() as session:
        before = get_plan_run(session, uuid.UUID(plan_run_id))
    assert before is not None
    original_recommendation = before.result.get("recommendation")
    reevaluated = seeded_client.post(f"/trips/{trip_id}/reevaluate")
    assert reevaluated.status_code == 200
    body = reevaluated.json()
    assert body["latest_plan_run_id"] != plan_run_id
    assert body["last_change_summary"] is not None
    Session = create_sessionmaker(_operator_url(migrated_test_database))
    with Session() as session:
        old_run = get_plan_run(session, uuid.UUID(plan_run_id))
        assert old_run is not None
        assert old_run.result.get("recommendation") == original_recommendation


def test_delete_trip_removes_from_list(seeded_client: TestClient) -> None:
    plan_run_id = _create_plan(seeded_client)
    trip_id = _save_trip(seeded_client, plan_run_id)
    deleted = seeded_client.delete(f"/trips/{trip_id}")
    assert deleted.status_code == 204
    listed = seeded_client.get("/trips")
    assert listed.json()["trips"] == []


def test_inactive_trip_expires(
    seeded_client: TestClient,
    migrated_test_database: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TRIP_INACTIVITY_DAYS", "90")
    plan_run_id = _create_plan(seeded_client)
    trip_id = _save_trip(seeded_client, plan_run_id)
    Session = create_sessionmaker(_operator_url(migrated_test_database))
    stale = datetime.now(timezone.utc) - timedelta(days=91)
    with Session() as session:
        trip = session.get(TripRecord, uuid.UUID(trip_id))
        assert trip is not None
        trip.last_activity_at = stale
        session.commit()
    listed = seeded_client.get("/trips")
    assert listed.json()["trips"] == []


def test_share_link_and_invalidations(seeded_client: TestClient) -> None:
    plan_run_id = _create_plan(seeded_client)
    trip_id = _save_trip(seeded_client, plan_run_id)
    shared = seeded_client.post(f"/trips/{trip_id}/share")
    assert shared.status_code == 200
    token = shared.json()["share_token"]
    snapshot = TestClient(app).get(f"/shares/{token}")
    assert snapshot.status_code == 200
    body = snapshot.json()
    assert "origin" not in body
    assert body["origin_region"] is not None
    assert body["plan_run_id"] == plan_run_id

    rotated = seeded_client.post(f"/trips/{trip_id}/share")
    new_token = rotated.json()["share_token"]
    assert TestClient(app).get(f"/shares/{token}").status_code == 404
    assert TestClient(app).get(f"/shares/{new_token}").status_code == 200

    deleted = seeded_client.delete(f"/trips/{trip_id}")
    assert deleted.status_code == 204
    assert TestClient(app).get(f"/shares/{new_token}").status_code == 404
