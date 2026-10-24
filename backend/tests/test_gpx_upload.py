from __future__ import annotations

import os
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import Response
from fastapi.testclient import TestClient
from sqlalchemy import func
from sqlalchemy import select

from app.db import create_sessionmaker
from app.domain.route import Assessment
from app.domain.route import Completeness
from app.domain.route import Provenance
from app.domain.route import Publication
from app.domain.route import RegionCoverage
from app.domain.route import TransitAccessibility
from app.gpx.process import GPX_DEFAULT_DESCRIPTION
from app.models.route import RouteRecord
from app.repositories.routes import get_route
from app.repositories.routes import list_route_revisions
from tests.test_route_search import _operator_url

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL is unset",
)

pytest_plugins = ["tests.test_route_search"]

_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "gpx"


def _read_fixture(name: str) -> bytes:
    return (_FIXTURES / name).read_bytes()


def _upload_form(**overrides: str) -> dict[str, str]:
    payload = {
        "name": "Uploaded Alpine Track",
        "route_type": "alpine_hike",
        "region_name": "Test Alps",
        "region_country": "AT",
    }
    payload.update(overrides)
    return payload


def _post_gpx(
    client: TestClient,
    gpx_bytes: bytes,
    *,
    filename: str = "track.gpx",
    form: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
) -> Response:
    data = _upload_form() if form is None else form
    files = {"file": (filename, gpx_bytes, "application/gpx+xml")}
    return client.post(
        "/routes/gpx-upload",
        data=data,
        files=files,
        headers=headers or {},
    )


def _route_count(migrated_test_database: str) -> int:
    Session = create_sessionmaker(_operator_url(migrated_test_database))
    with Session() as session:
        return session.scalar(select(func.count()).select_from(RouteRecord)) or 0


def test_valid_minimal_gpx_returns_201_with_quarantined_state(
    seeded_client: TestClient,
    migrated_test_database: str,
) -> None:
    response = _post_gpx(seeded_client, _read_fixture("valid_minimal.gpx"))
    assert response.status_code == 201
    body = response.json()
    route_id = uuid.UUID(body["id"])
    assert body["publication"] == "quarantined"
    assert body["provenance"] == "gpx_upload"

    Session = create_sessionmaker(_operator_url(migrated_test_database))
    with Session() as session:
        route = get_route(session, route_id)
        assert route is not None
        assert route.completeness == Completeness.INCOMPLETE
        assert route.assessment == Assessment.UNASSESSED
        assert route.duration_minutes is None
        assert route.duration_is_estimated is False
        assert route.region.coverage == RegionCoverage.UNSUPPORTED
        assert route.transit_accessibility == TransitAccessibility.UNKNOWN
        assert route.season_months == set()
        assert route.difficulty is None
        assert route.closure_assessment is None
        assert route.description == GPX_DEFAULT_DESCRIPTION
        assert route.trailhead is not None
        assert route.linestring is not None
        assert len(route.linestring.points) >= 2
        assert route.gpx is not None
        assert "<extensions>" not in route.gpx
        assert "<link" not in route.gpx.lower()
        assert route.elevation_min_m == 1200
        assert route.elevation_max_m == 1250
        assert route.elevation_gain_m == 50
        assert route.elevation_loss_m == 20

        revisions = list_route_revisions(session, route_id)
        assert len(revisions) == 1
        assert revisions[0].author_kind == "anonymous"
        assert revisions[0].author_ref is None


def test_anonymous_id_stored_as_author_ref(
    seeded_client: TestClient,
    migrated_test_database: str,
) -> None:
    response = _post_gpx(
        seeded_client,
        _read_fixture("valid_minimal.gpx"),
        headers={"X-ClimbIt-Anonymous-Id": "anon-upload-42"},
    )
    assert response.status_code == 201
    route_id = uuid.UUID(response.json()["id"])
    Session = create_sessionmaker(_operator_url(migrated_test_database))
    with Session() as session:
        revisions = list_route_revisions(session, route_id)
    assert revisions[0].author_ref == "anon-upload-42"


def test_one_byte_over_limit_returns_413_without_route_row(
    seeded_client: TestClient,
    migrated_test_database: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MAX_GPX_UPLOAD_BYTES", "100")
    before = _route_count(migrated_test_database)
    payload = b"x" * 101
    response = _post_gpx(seeded_client, payload)
    assert response.status_code == 413
    assert _route_count(migrated_test_database) == before


def test_malformed_xml_returns_422_without_route_row(
    seeded_client: TestClient,
    migrated_test_database: str,
) -> None:
    before = _route_count(migrated_test_database)
    response = _post_gpx(seeded_client, _read_fixture("malformed.gpx"))
    assert response.status_code == 422
    assert _route_count(migrated_test_database) == before


def test_single_point_track_returns_422_without_route_row(
    seeded_client: TestClient,
    migrated_test_database: str,
) -> None:
    before = _route_count(migrated_test_database)
    response = _post_gpx(seeded_client, _read_fixture("single_point.gpx"))
    assert response.status_code == 422
    assert _route_count(migrated_test_database) == before


def test_no_elevation_returns_201_with_null_elevations(
    seeded_client: TestClient,
    migrated_test_database: str,
) -> None:
    response = _post_gpx(seeded_client, _read_fixture("no_elevation.gpx"))
    assert response.status_code == 201
    route_id = uuid.UUID(response.json()["id"])
    Session = create_sessionmaker(_operator_url(migrated_test_database))
    with Session() as session:
        route = get_route(session, route_id)
    assert route is not None
    assert route.elevation_min_m is None
    assert route.elevation_max_m is None
    assert route.elevation_gain_m is None
    assert route.elevation_loss_m is None
    assert "<ele>" not in (route.gpx or "")


def test_uploaded_route_hidden_from_search_and_detail_plan(
    seeded_client: TestClient,
) -> None:
    response = _post_gpx(seeded_client, _read_fixture("valid_minimal.gpx"))
    assert response.status_code == 201
    route_id = response.json()["id"]

    listed = seeded_client.get("/routes").json()["routes"]
    assert route_id not in {item["id"] for item in listed}

    detail = seeded_client.get(f"/routes/{route_id}")
    assert detail.status_code == 404

    plan = seeded_client.post(
        f"/routes/{route_id}/plans",
        json={"plan_date": "2026-07-15", "origin": "Innsbruck Hbf"},
    )
    assert plan.status_code == 404


def test_external_link_gpx_does_not_fetch_urls(seeded_client: TestClient) -> None:
    with patch("urllib.request.urlopen") as urlopen:
        response = _post_gpx(seeded_client, _read_fixture("external_link.gpx"))
    assert response.status_code == 201
    urlopen.assert_not_called()
