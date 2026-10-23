import os
import uuid
from collections.abc import Iterator
from datetime import datetime
from datetime import timedelta
from datetime import timezone

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from psycopg import sql
from sqlalchemy import text

from app.db import create_engine_from_database_url
from app.db import create_sessionmaker
from app.db import sqlalchemy_url
from app.domain.closure import ClosureAssessment
from app.domain.closure import ClosureReviewStatus
from app.domain.closure import ClosureStatus
from app.domain.difficulty import Difficulty
from app.domain.difficulty import MappingConfidence
from app.domain.difficulty import map_difficulty
from app.domain.route import Assessment
from app.domain.route import Completeness
from app.domain.route import LineString
from app.domain.route import Point
from app.domain.route import Provenance
from app.domain.route import Publication
from app.domain.route import Region
from app.domain.route import RegionCoverage
from app.domain.route import Route
from app.domain.route import RouteType
from app.domain.route import TransitAccessibility
from app.repositories.routes import get_route
from app.repositories.routes import save_route

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL is unset",
)

_MISSING_RELATIONS = (
    "public.regions",
    "public.users",
    "public.revisions",
)


def _backend_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _alembic_config() -> Config:
    return Config(os.path.join(_backend_root(), "alembic.ini"))


def _operator_url(database: str | None = None) -> str:
    url = sqlalchemy_url(os.environ["DATABASE_URL"])
    if database is not None:
        url = url.set(database=database)
    return url.set(drivername="postgresql").render_as_string(hide_password=False)


def _connect(admin_url: str, database: str | None = None) -> psycopg.Connection:
    url = sqlalchemy_url(admin_url)
    return psycopg.connect(
        host=url.host,
        port=url.port or 5432,
        user=url.username,
        password=url.password,
        dbname=database or url.database,
        autocommit=True,
    )


def _database_exists(admin_url: str, name: str) -> bool:
    with _connect(admin_url) as conn:
        row = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            [name],
        ).fetchone()
        return row is not None


@pytest.fixture
def migrated_test_database() -> Iterator[str]:
    admin_url = os.environ["DATABASE_URL"]
    admin_database = sqlalchemy_url(admin_url).database
    test_database = f"test_{uuid.uuid4().hex}"
    assert test_database.startswith("test_")
    assert test_database != "climbit"
    assert test_database != admin_database

    with _connect(admin_url) as conn:
        conn.execute(
            sql.SQL("CREATE DATABASE {}").format(sql.Identifier(test_database))
        )

    os.environ["DATABASE_URL"] = _operator_url(test_database)
    try:
        command.upgrade(_alembic_config(), "head")
        yield test_database
    finally:
        os.environ["DATABASE_URL"] = admin_url
        with _connect(admin_url) as conn:
            conn.execute(
                sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(
                    sql.Identifier(test_database)
                )
            )
        assert _database_exists(admin_url, admin_database)
        assert _database_exists(admin_url, "climbit")
        assert not _database_exists(admin_url, test_database)


@pytest.fixture
def session(migrated_test_database: str) -> Iterator:
    Session = create_sessionmaker(_operator_url(migrated_test_database))
    db_session = Session()
    bind = db_session.get_bind()
    try:
        yield db_session
        db_session.commit()
    finally:
        db_session.close()
        bind.dispose()


def _region(**overrides) -> Region:
    payload = {
        "name": "Allgäu",
        "country": "DE",
        "coverage": RegionCoverage.SUPPORTED,
    }
    payload.update(overrides)
    return Region(**payload)


def _point(*, longitude: float = 10.0, latitude: float = 47.0) -> Point:
    return Point(longitude=longitude, latitude=latitude)


def _linestring(*points: Point) -> LineString:
    if not points:
        points = (_point(), _point(longitude=10.1, latitude=47.1))
    return LineString(points=list(points))


def _route(**overrides) -> Route:
    payload = {
        "name": "Hindelanger Klettersteig",
        "route_type": RouteType.ALPINE_HIKE,
        "region": _region(),
        "publication": Publication.QUARANTINED,
        "trailhead": None,
        "linestring": None,
        "gpx": None,
        "elevation_min_m": None,
        "elevation_max_m": None,
        "elevation_gain_m": None,
        "elevation_loss_m": None,
        "duration_minutes": None,
        "approach_minutes": None,
        "technical_minutes": None,
        "descent_minutes": None,
        "duration_is_estimated": True,
        "original_difficulty_value": None,
        "original_difficulty_scale": None,
        "season_months": set(),
        "season_note": None,
        "description": "",
        "transit_accessibility": TransitAccessibility.UNKNOWN,
        "official_source_links": [],
        "provenance": Provenance.SEED,
        "completeness": Completeness.INCOMPLETE,
        "assessment": Assessment.UNASSESSED,
    }
    payload.update(overrides)
    return Route(**payload)


def _closure(**overrides) -> ClosureAssessment:
    utc = timezone.utc
    payload = {
        "status": ClosureStatus.NONE_KNOWN,
        "source_url": "https://example.invalid/closure-notice",
        "owner": "maintainer",
        "review_status": ClosureReviewStatus.REVIEWED,
        "created_at": datetime(2026, 7, 15, 12, 0, 0, tzinfo=utc),
        "updated_at": datetime(2026, 7, 16, 12, 0, 0, tzinfo=utc),
        "reviewed_at": datetime(2026, 7, 16, 12, 0, 0, tzinfo=utc),
        "expires_at": datetime(2026, 8, 1, 12, 0, 0, tzinfo=utc),
    }
    payload.update(overrides)
    return ClosureAssessment(**payload)


def _assert_point(actual: Point | None, expected: Point | None) -> None:
    if expected is None:
        assert actual is None
        return
    assert actual is not None
    assert actual.longitude == pytest.approx(expected.longitude)
    assert actual.latitude == pytest.approx(expected.latitude)


def _assert_linestring(actual: LineString | None, expected: LineString | None) -> None:
    if expected is None:
        assert actual is None
        return
    assert actual is not None
    assert len(actual.points) == len(expected.points)
    for got, want in zip(actual.points, expected.points, strict=True):
        _assert_point(got, want)


def _assert_route_roundtrip(loaded: Route, saved: Route) -> None:
    assert loaded.name == saved.name
    assert loaded.route_type is saved.route_type
    assert loaded.region == saved.region
    assert loaded.publication is saved.publication
    _assert_point(loaded.trailhead, saved.trailhead)
    _assert_linestring(loaded.linestring, saved.linestring)
    assert loaded.gpx == saved.gpx
    assert loaded.elevation_min_m == saved.elevation_min_m
    assert loaded.elevation_max_m == saved.elevation_max_m
    assert loaded.elevation_gain_m == saved.elevation_gain_m
    assert loaded.elevation_loss_m == saved.elevation_loss_m
    assert loaded.duration_minutes == saved.duration_minutes
    assert loaded.approach_minutes == saved.approach_minutes
    assert loaded.technical_minutes == saved.technical_minutes
    assert loaded.descent_minutes == saved.descent_minutes
    assert loaded.duration_is_estimated is saved.duration_is_estimated
    assert loaded.original_difficulty_value == saved.original_difficulty_value
    assert loaded.original_difficulty_scale == saved.original_difficulty_scale
    assert loaded.difficulty == saved.difficulty
    assert loaded.closure_assessment == saved.closure_assessment
    assert loaded.season_months == saved.season_months
    assert loaded.season_note == saved.season_note
    assert loaded.description == saved.description
    assert loaded.transit_accessibility is saved.transit_accessibility
    assert loaded.official_source_links == saved.official_source_links
    assert loaded.provenance is saved.provenance
    assert loaded.completeness is saved.completeness
    assert loaded.assessment is saved.assessment


def _roundtrip(session, route: Route) -> Route:
    route_id = save_route(session, route)
    session.commit()
    loaded = get_route(session, route_id)
    assert loaded is not None
    return loaded


def test_upgrade_head_creates_routes_table_only(migrated_test_database: str) -> None:
    script = ScriptDirectory.from_config(_alembic_config())
    heads = script.get_heads()
    assert len(heads) == 1
    assert heads[0] == "d2e3f4a5b6c7"
    assert script.get_revision(heads[0]).down_revision == "c1d2e3f4a5b6"

    engine = create_engine_from_database_url(_operator_url(migrated_test_database))
    try:
        with engine.connect() as connection:
            routes = connection.execute(text("SELECT to_regclass('public.routes')")).scalar()
            assert str(routes) == "routes"
            route_revisions = connection.execute(
                text("SELECT to_regclass('public.route_revisions')")
            ).scalar()
            assert str(route_revisions) == "route_revisions"
            plan_runs = connection.execute(
                text("SELECT to_regclass('public.plan_runs')")
            ).scalar()
            assert str(plan_runs) == "plan_runs"
            trip_capabilities = connection.execute(
                text("SELECT to_regclass('public.trip_capabilities')")
            ).scalar()
            assert str(trip_capabilities) == "trip_capabilities"
            trips = connection.execute(text("SELECT to_regclass('public.trips')")).scalar()
            assert str(trips) == "trips"
            for relation in _MISSING_RELATIONS:
                assert connection.execute(
                    text("SELECT to_regclass(:name)"),
                    {"name": relation},
                ).scalar() is None
            connection.execute(text("SELECT PostGIS_Version()"))
            safety = connection.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'routes'
                      AND (
                        column_name = 'safety_buffer'
                        OR column_name LIKE '%safety_buffer%'
                      )
                    """
                )
            ).fetchall()
            assert safety == []

            id_row = connection.execute(
                text(
                    """
                    SELECT data_type, column_default, is_identity, identity_generation
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'routes'
                      AND column_name = 'id'
                    """
                )
            ).one()
            assert id_row[0] == "uuid"
            assert id_row[1] is None
            assert id_row[2] == "NO"
            assert id_row[3] is None

            geom_rows = connection.execute(
                text(
                    """
                    SELECT f_geometry_column, type, srid
                    FROM geometry_columns
                    WHERE f_table_schema = 'public' AND f_table_name = 'routes'
                    ORDER BY f_geometry_column
                    """
                )
            ).fetchall()
            geom = {row[0]: (row[1], row[2]) for row in geom_rows}
            assert geom["trailhead"] == ("POINT", 4326)
            assert geom["linestring"] == ("LINESTRING", 4326)

            json_rows = connection.execute(
                text(
                    """
                    SELECT column_name, data_type, udt_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'routes'
                      AND column_name IN ('season_months', 'official_source_links')
                    """
                )
            ).fetchall()
            json_types = {row[0]: (row[1], row[2]) for row in json_rows}
            assert json_types["season_months"][1] == "jsonb"
            assert json_types["official_source_links"][1] == "jsonb"
            assert json_types["season_months"][0] != "ARRAY"
            assert json_types["official_source_links"][0] != "ARRAY"

            enum_count = connection.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM information_schema.columns c
                    JOIN pg_type t ON t.typname = c.udt_name
                    WHERE c.table_schema = 'public'
                      AND c.table_name = 'routes'
                      AND t.typtype = 'e'
                    """
                )
            ).scalar()
            assert enum_count == 0

            timestamptz_cols = connection.execute(
                text(
                    """
                    SELECT column_name, udt_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'routes'
                      AND column_name LIKE 'closure_%_at'
                    """
                )
            ).fetchall()
            assert {row[0] for row in timestamptz_cols} == {
                "closure_created_at",
                "closure_updated_at",
                "closure_reviewed_at",
                "closure_expires_at",
            }
            assert {row[1] for row in timestamptz_cols} == {"timestamptz"}
    finally:
        engine.dispose()


def test_roundtrip_published_klettersteig(session) -> None:
    difficulty = map_difficulty(RouteType.KLETTERSTEIG, "K3", "k1_k6")
    saved = _route(
        name="Klettersteig One",
        route_type=RouteType.KLETTERSTEIG,
        region=_region(coverage=RegionCoverage.SUPPORTED),
        publication=Publication.PUBLISHED,
        trailhead=_point(longitude=10.2, latitude=47.2),
        linestring=_linestring(
            _point(longitude=10.2, latitude=47.2),
            _point(longitude=10.3, latitude=47.3),
        ),
        gpx="<gpx>track</gpx>",
        elevation_min_m=800,
        elevation_max_m=1800,
        elevation_gain_m=1000,
        elevation_loss_m=200,
        duration_minutes=180,
        approach_minutes=40,
        technical_minutes=90,
        descent_minutes=50,
        duration_is_estimated=False,
        original_difficulty_value="K3",
        original_difficulty_scale="k1_k6",
        difficulty=difficulty,
        closure_assessment=_closure(),
        season_months={6, 7, 8},
        official_source_links=["https://example.invalid/source"],
        transit_accessibility=TransitAccessibility.TRANSIT_FRIENDLY,
        completeness=Completeness.COMPLETE,
        assessment=Assessment.CURRENT,
    )
    loaded = _roundtrip(session, saved)
    _assert_route_roundtrip(loaded, saved)
    assert loaded.difficulty is not None
    assert loaded.difficulty.mapped_huebler == difficulty.mapped_huebler
    assert loaded.closure_assessment is not None
    assert loaded.closure_assessment.status is ClosureStatus.NONE_KNOWN
    created = loaded.closure_assessment.created_at
    assert created.tzinfo is not None
    assert created.utcoffset() == timedelta(0)
    assert created == datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)


def test_roundtrip_published_alpine_hike(session) -> None:
    difficulty = map_difficulty(RouteType.ALPINE_HIKE, "T3", "SAC")
    saved = _route(
        name="Alpine Hike One",
        route_type=RouteType.ALPINE_HIKE,
        publication=Publication.PUBLISHED,
        trailhead=_point(),
        linestring=_linestring(),
        gpx=None,
        elevation_min_m=900,
        elevation_max_m=1600,
        duration_minutes=240,
        approach_minutes=None,
        technical_minutes=None,
        descent_minutes=None,
        duration_is_estimated=True,
        original_difficulty_value="T3",
        original_difficulty_scale="SAC",
        difficulty=difficulty,
        closure_assessment=None,
        season_months=set(),
        official_source_links=[],
    )
    loaded = _roundtrip(session, saved)
    _assert_route_roundtrip(loaded, saved)
    assert loaded.closure_assessment is None
    assert loaded.gpx is None
    assert loaded.season_months == set()
    assert loaded.official_source_links == []
    assert loaded.duration_is_estimated is True


def test_roundtrip_quarantined_outdoor_climbing(session) -> None:
    difficulty = map_difficulty(RouteType.OUTDOOR_CLIMBING, "6a", "French")
    saved = _route(
        name="Outdoor Climb One",
        route_type=RouteType.OUTDOOR_CLIMBING,
        publication=Publication.QUARANTINED,
        trailhead=None,
        linestring=None,
        elevation_min_m=None,
        elevation_max_m=None,
        duration_minutes=None,
        approach_minutes=None,
        technical_minutes=None,
        descent_minutes=None,
        duration_is_estimated=True,
        original_difficulty_value="6a",
        original_difficulty_scale="French",
        difficulty=difficulty,
        closure_assessment=None,
    )
    loaded = _roundtrip(session, saved)
    _assert_route_roundtrip(loaded, saved)
    assert loaded.trailhead is None
    assert loaded.linestring is None
    assert loaded.publication is Publication.QUARANTINED


def test_awkward_persistence_cases(session, monkeypatch) -> None:
    trailhead = _point(longitude=11.0, latitude=46.5)
    three_point_line = _linestring(
        _point(longitude=10.0, latitude=47.0),
        _point(longitude=10.05, latitude=47.02),
        _point(longitude=10.1, latitude=47.05),
    )
    unreviewed = _closure(
        review_status=ClosureReviewStatus.UNREVIEWED,
        reviewed_at=None,
        updated_at=datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc),
    )
    saved = _route(
        publication=Publication.QUARANTINED,
        trailhead=trailhead,
        linestring=three_point_line,
        elevation_min_m=1200,
        elevation_max_m=1200,
        closure_assessment=unreviewed,
        duration_is_estimated=True,
    )
    assert trailhead.longitude != three_point_line.points[0].longitude

    def boom(*_args, **_kwargs):
        raise AssertionError("domain mapping or planning function invoked")

    monkeypatch.setattr("app.domain.difficulty.map_difficulty", boom)
    monkeypatch.setattr("app.domain.closure.closure_planning_input", boom)

    loaded = _roundtrip(session, saved)
    _assert_route_roundtrip(loaded, saved)
    assert loaded.linestring is not None
    assert len(loaded.linestring.points) == 3
    assert loaded.elevation_min_m == loaded.elevation_max_m
    assert loaded.closure_assessment is not None
    assert loaded.closure_assessment.reviewed_at is None


def test_stored_unmapped_difficulty_is_not_remapped(session) -> None:
    meta = map_difficulty(RouteType.KLETTERSTEIG, None, None)
    stored_unmapped = Difficulty(
        route_type=RouteType.KLETTERSTEIG,
        original_value="K3",
        original_scale="k1_k6",
        structured_scale=None,
        structured_value=None,
        mapped_huebler=None,
        mapping_confidence=MappingConfidence.UNMAPPED,
        mapping_source=meta.mapping_source,
        mapping_citation=meta.mapping_citation,
        mapping_version=meta.mapping_version,
    )
    saved = _route(
        route_type=RouteType.KLETTERSTEIG,
        original_difficulty_value="K3",
        original_difficulty_scale="k1_k6",
        difficulty=stored_unmapped,
    )
    loaded = _roundtrip(session, saved)
    assert loaded.difficulty is not None
    assert loaded.difficulty.mapping_confidence is MappingConfidence.UNMAPPED
    assert loaded.difficulty.mapped_huebler is None
    assert loaded.difficulty.structured_scale is None


def test_get_route_missing_uuid_returns_none(session) -> None:
    assert get_route(session, uuid.uuid4()) is None


def test_save_route_returns_application_uuid(session) -> None:
    route_id = save_route(session, _route())
    session.commit()
    assert isinstance(route_id, uuid.UUID)
    loaded = get_route(session, route_id)
    assert loaded is not None


def test_null_difficulty_and_closure_roundtrip(session) -> None:
    saved = _route(difficulty=None, closure_assessment=None)
    loaded = _roundtrip(session, saved)
    assert loaded.difficulty is None
    assert loaded.closure_assessment is None
