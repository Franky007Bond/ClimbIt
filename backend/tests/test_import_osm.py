from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func
from sqlalchemy import select

from app.db import create_sessionmaker
from app.domain.route import Assessment
from app.domain.route import Completeness
from app.domain.route import Provenance
from app.domain.route import Publication
from app.domain.route import Region
from app.domain.route import RegionCoverage
from app.domain.route import Route
from app.domain.route import RouteType
from app.domain.route import TransitAccessibility
from app.import_osm import OsmImportConflictError
from app.import_osm import import_osm_routes
from app.models.route import RouteRecord
from app.osm.geometry import OsmGeometryError
from app.osm.geometry import parse_overpass_geometry
from app.osm.import_route import OSM_COPYRIGHT_URL
from app.osm.import_route import build_osm_import_route
from app.osm.import_route import format_import_description
from app.osm.import_route import osm_object_url
from app.osm.import_route import osm_route_id
from app.osm.manifest import ImportManifest
from app.osm.manifest import ManifestEntry
from app.osm.manifest import OsmElementType
from app.osm.manifest import load_manifest
from app.osm.overpass import UrllibOverpassClient
from app.repositories.routes import get_route
from app.repositories.routes import list_route_revisions
from app.repositories.routes import upsert_route
from tests.test_route_search import _operator_url

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL is unset",
)

pytest_plugins = ["tests.test_route_search"]

_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "osm"
_FIXED_IMPORT_TIME = datetime(2026, 3, 15, 12, 30, 0, tzinfo=timezone.utc)


def _read_json(name: str) -> dict[str, Any]:
    return json.loads((_FIXTURES / name).read_text(encoding="utf-8"))


class _StubOverpassClient:
    def __init__(self, responses: dict[tuple[str, int], dict[str, Any]]) -> None:
        self._responses = responses
        self.calls: list[tuple[str, int]] = []

    def fetch_element(self, osm_type: OsmElementType, osm_id: int) -> dict[str, Any]:
        self.calls.append((osm_type.value, osm_id))
        key = (osm_type.value, osm_id)
        if key not in self._responses:
            msg = f"unexpected Overpass request: {key}"
            raise AssertionError(msg)
        return self._responses[key]


def _stub_for_manifest(manifest: ImportManifest) -> _StubOverpassClient:
    mapping = {
        1001: "way_with_elevation.json",
        1002: "way_no_elevation.json",
    }
    responses: dict[tuple[str, int], dict[str, Any]] = {}
    for entry in manifest.entries:
        fixture_name = mapping.get(entry.osm_id)
        if fixture_name is None:
            msg = f"no fixture mapping for osm_id {entry.osm_id}"
            raise ValueError(msg)
        responses[(entry.osm_type.value, entry.osm_id)] = _read_json(fixture_name)
    return _StubOverpassClient(responses)


def test_build_osm_import_route_rejects_published_publication() -> None:
    entry = ManifestEntry(
        osm_type=OsmElementType.WAY,
        osm_id=42,
        name="Test",
        route_type=RouteType.ALPINE_HIKE,
        region_name="Alps",
        region_country="AT",
    )
    geometry = parse_overpass_geometry(
        _read_json("way_with_elevation.json"),
        osm_type="way",
        osm_id=1001,
    )
    with pytest.raises(ValueError, match="quarantined"):
        build_osm_import_route(
            entry=entry,
            geometry=geometry,
            imported_at=_FIXED_IMPORT_TIME,
            publication=Publication.PUBLISHED,
        )


def test_parse_overpass_geometry_elevation_and_no_elevation() -> None:
    with_ele = parse_overpass_geometry(
        _read_json("way_with_elevation.json"),
        osm_type="way",
        osm_id=1001,
    )
    assert with_ele.elevation_min_m == 1200
    assert with_ele.elevation_max_m == 1250
    assert with_ele.elevation_gain_m == 50
    assert with_ele.elevation_loss_m == 0

    without_ele = parse_overpass_geometry(
        _read_json("way_no_elevation.json"),
        osm_type="way",
        osm_id=1002,
    )
    assert without_ele.elevation_min_m is None
    assert without_ele.elevation_max_m is None
    assert without_ele.elevation_gain_m is None
    assert without_ele.elevation_loss_m is None


def test_import_osm_persists_quarantined_routes(
    migrated_test_database: str,
) -> None:
    manifest = load_manifest(str(_FIXTURES / "manifest.json"))
    overpass = _stub_for_manifest(manifest)
    Session = create_sessionmaker(_operator_url(migrated_test_database))
    with Session() as session:
        route_ids = import_osm_routes(
            session,
            manifest,
            overpass=overpass,
            imported_at=_FIXED_IMPORT_TIME,
        )
        session.commit()

    assert len(route_ids) == 2
    way_with_ele_id = osm_route_id("way", 1001)
    way_no_ele_id = osm_route_id("way", 1002)
    assert route_ids == [way_with_ele_id, way_no_ele_id]

    Session = create_sessionmaker(_operator_url(migrated_test_database))
    with Session() as session:
        with_ele = get_route(session, way_with_ele_id)
        without_ele = get_route(session, way_no_ele_id)
    assert with_ele is not None
    assert without_ele is not None

    expected_description = format_import_description(_FIXED_IMPORT_TIME)
    assert with_ele.publication is Publication.QUARANTINED
    assert with_ele.provenance is Provenance.OSM
    assert with_ele.completeness is Completeness.INCOMPLETE
    assert with_ele.assessment is Assessment.UNASSESSED
    assert with_ele.region.coverage is RegionCoverage.UNSUPPORTED
    assert with_ele.transit_accessibility is TransitAccessibility.UNKNOWN
    assert with_ele.season_months == set()
    assert with_ele.difficulty is None
    assert with_ele.closure_assessment is None
    assert with_ele.description == expected_description
    assert "© OpenStreetMap contributors" in with_ele.description
    assert with_ele.official_source_links == [
        OSM_COPYRIGHT_URL,
        osm_object_url("way", 1001),
    ]
    assert with_ele.duration_minutes is None
    assert with_ele.duration_is_estimated is False

    assert without_ele.duration_minutes == 240
    assert without_ele.duration_is_estimated is True

    Session = create_sessionmaker(_operator_url(migrated_test_database))
    with Session() as session:
        revisions = list_route_revisions(session, way_with_ele_id)
    assert len(revisions) == 1
    assert revisions[0].author_kind == "system"


def test_reimport_upserts_osm_quarantined_route(migrated_test_database: str) -> None:
    manifest = load_manifest(str(_FIXTURES / "manifest.json"))
    overpass = _stub_for_manifest(manifest)
    Session = create_sessionmaker(_operator_url(migrated_test_database))
    with Session() as session:
        import_osm_routes(session, manifest, overpass=overpass, imported_at=_FIXED_IMPORT_TIME)
        session.commit()
        import_osm_routes(session, manifest, overpass=overpass, imported_at=_FIXED_IMPORT_TIME)
        session.commit()

    Session = create_sessionmaker(_operator_url(migrated_test_database))
    with Session() as session:
        count = session.scalar(select(func.count()).select_from(RouteRecord)) or 0
    assert count == 2


def test_import_conflict_when_existing_route_not_osm_quarantined(
    migrated_test_database: str,
) -> None:
    conflict_id = osm_route_id("way", 1001)
    conflicting = Route(
        name="Published blocker",
        route_type=RouteType.ALPINE_HIKE,
        region=Region(name="Alps", country="AT", coverage=RegionCoverage.SUPPORTED),
        publication=Publication.PUBLISHED,
        trailhead=parse_overpass_geometry(
            _read_json("way_with_elevation.json"),
            osm_type="way",
            osm_id=1001,
        ).trailhead,
        linestring=parse_overpass_geometry(
            _read_json("way_with_elevation.json"),
            osm_type="way",
            osm_id=1001,
        ).linestring,
        gpx=None,
        elevation_min_m=1200,
        elevation_max_m=1250,
        elevation_gain_m=50,
        elevation_loss_m=0,
        duration_minutes=120,
        approach_minutes=None,
        technical_minutes=None,
        descent_minutes=None,
        duration_is_estimated=False,
        original_difficulty_value=None,
        original_difficulty_scale=None,
        difficulty=None,
        closure_assessment=None,
        season_months={6, 7, 8},
        season_note=None,
        description="seed conflict",
        transit_accessibility=TransitAccessibility.UNKNOWN,
        official_source_links=["https://example.com/route"],
        provenance=Provenance.SEED,
        completeness=Completeness.COMPLETE,
        assessment=Assessment.CURRENT,
    )
    Session = create_sessionmaker(_operator_url(migrated_test_database))
    with Session() as session:
        upsert_route(session, conflict_id, conflicting, author_kind="system")
        session.commit()

    manifest = ImportManifest(
        entries=[
            ManifestEntry(
                osm_type=OsmElementType.WAY,
                osm_id=1001,
                name="Should fail",
                route_type=RouteType.ALPINE_HIKE,
                region_name="Fixture Alps",
                region_country="AT",
            )
        ]
    )
    overpass = _StubOverpassClient({("way", 1001): _read_json("way_with_elevation.json")})
    Session = create_sessionmaker(_operator_url(migrated_test_database))
    with Session() as session:
        with pytest.raises(OsmImportConflictError, match="way/1001"):
            import_osm_routes(session, manifest, overpass=overpass)
        session.rollback()

    Session = create_sessionmaker(_operator_url(migrated_test_database))
    with Session() as session:
        count = session.scalar(select(func.count()).select_from(RouteRecord)) or 0
    assert count == 1


def test_invalid_geometry_rolls_back_entire_import(migrated_test_database: str) -> None:
    manifest = ImportManifest(
        entries=[
            ManifestEntry(
                osm_type=OsmElementType.WAY,
                osm_id=1001,
                name="Good first",
                route_type=RouteType.ALPINE_HIKE,
                region_name="Fixture Alps",
                region_country="AT",
            ),
            ManifestEntry(
                osm_type=OsmElementType.WAY,
                osm_id=1999,
                name="Bad second",
                route_type=RouteType.ALPINE_HIKE,
                region_name="Fixture Alps",
                region_country="AT",
            ),
        ]
    )
    overpass = _StubOverpassClient(
        {
            ("way", 1001): _read_json("way_with_elevation.json"),
            ("way", 1999): _read_json("way_single_point.json"),
        }
    )
    Session = create_sessionmaker(_operator_url(migrated_test_database))
    with Session() as session:
        with pytest.raises(OsmGeometryError):
            import_osm_routes(session, manifest, overpass=overpass)
        session.rollback()

    Session = create_sessionmaker(_operator_url(migrated_test_database))
    with Session() as session:
        count = session.scalar(select(func.count()).select_from(RouteRecord)) or 0
    assert count == 0


def test_imported_routes_hidden_from_search_and_detail(
    seeded_client: TestClient,
    migrated_test_database: str,
) -> None:
    manifest = load_manifest(str(_FIXTURES / "manifest.json"))
    overpass = _stub_for_manifest(manifest)
    Session = create_sessionmaker(_operator_url(migrated_test_database))
    with Session() as session:
        route_ids = import_osm_routes(
            session,
            manifest,
            overpass=overpass,
            imported_at=_FIXED_IMPORT_TIME,
        )
        session.commit()

    listed = seeded_client.get("/routes").json()["routes"]
    listed_ids = {item["id"] for item in listed}
    for route_id in route_ids:
        assert str(route_id) not in listed_ids
        detail = seeded_client.get(f"/routes/{route_id}")
        assert detail.status_code == 404


def test_urllib_overpass_client_retries_429_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OVERPASS_API_URL", "http://overpass.test/interpreter")
    client = UrllibOverpassClient(api_url="http://overpass.test/interpreter", min_interval_seconds=0)

    class _FakeHTTPError(Exception):
        def __init__(self, code: int) -> None:
            self.code = code

    responses = [
        _FakeHTTPError(429),
        _FakeHTTPError(429),
        json.dumps({"elements": []}).encode("utf-8"),
    ]

    def fake_urlopen(_request: object, timeout: float = 0) -> object:
        item = responses.pop(0)
        if isinstance(item, Exception):
            import urllib.error

            raise urllib.error.HTTPError(
                url="http://overpass.test/interpreter",
                code=item.code,
                msg="rate limited",
                hdrs=None,
                fp=None,
            )
        return _FakeResponse(item)

    class _FakeResponse:
        def __init__(self, body: bytes) -> None:
            self._body = body

        def read(self) -> bytes:
            return self._body

        def __enter__(self) -> _FakeResponse:
            return self

        def __exit__(self, *args: object) -> None:
            return None

    with patch("app.osm.overpass.time.sleep"), patch(
        "urllib.request.urlopen",
        side_effect=fake_urlopen,
    ):
        payload = client.fetch_element(OsmElementType.WAY, 1001)

    assert payload == {"elements": []}


def test_overpass_client_enforces_min_interval(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OVERPASS_API_URL", "http://overpass.test/interpreter")
    client = UrllibOverpassClient(api_url="http://overpass.test/interpreter", min_interval_seconds=2)
    payload = {"elements": []}

    with patch("app.osm.overpass.time.sleep") as sleep, patch(
        "urllib.request.urlopen",
        return_value=_FakeUrlopenResponse(json.dumps(payload).encode("utf-8")),
    ):
        client.fetch_element(OsmElementType.WAY, 1)
        client.fetch_element(OsmElementType.WAY, 2)

    sleep.assert_called_once()
    assert sleep.call_args.args[0] == pytest.approx(2.0, rel=0.5)


class _FakeUrlopenResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeUrlopenResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None
