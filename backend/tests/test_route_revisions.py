import os
import uuid
from collections.abc import Iterator
from datetime import datetime
from datetime import timezone

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from psycopg import sql
from sqlalchemy import select
from sqlalchemy import text

from app.db import create_sessionmaker
from app.db import sqlalchemy_url
from app.domain.route import Publication
from app.domain.route import Provenance
from app.domain.route import Region
from app.domain.route import RegionCoverage
from app.domain.route import Route
from app.domain.route import RouteType
from app.domain.route import TransitAccessibility
from app.domain.route import Completeness
from app.domain.route import Assessment
from app.models.route_revision import RouteRevisionRecord
from app.repositories.routes import list_route_revisions
from app.repositories.routes import save_route
from app.repositories.routes import upsert_route

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL is unset",
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


def _route(**overrides) -> Route:
    payload = {
        "name": "Revision Test Route",
        "route_type": RouteType.ALPINE_HIKE,
        "region": Region(
            name="Allgäu",
            country="DE",
            coverage=RegionCoverage.SUPPORTED,
        ),
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
        "description": "first description",
        "transit_accessibility": TransitAccessibility.UNKNOWN,
        "official_source_links": [],
        "provenance": Provenance.SEED,
        "completeness": Completeness.INCOMPLETE,
        "assessment": Assessment.UNASSESSED,
    }
    payload.update(overrides)
    return Route(**payload)


def test_single_alembic_head_includes_route_revisions(migrated_test_database: str) -> None:
    script = ScriptDirectory.from_config(_alembic_config())
    heads = script.get_heads()
    assert len(heads) == 1
    assert heads[0] == "b7c8d9e0f1a2"
    route_revisions = script.get_revision("a3f1c2d4e5b6")
    assert route_revisions is not None
    assert route_revisions.down_revision == "855431646849"


def test_save_route_appends_revision_one(session) -> None:
    started = datetime.now(timezone.utc)
    route_id = save_route(session, _route())
    session.commit()
    finished = datetime.now(timezone.utc)

    revisions = list_route_revisions(session, route_id)
    assert len(revisions) == 1
    rev = revisions[0]
    assert rev.revision_number == 1
    assert rev.before_snapshot is None
    assert rev.after_snapshot["description"] == "first description"
    assert rev.application_status == "applied"
    assert rev.author_kind == "system"
    assert rev.author_ref is None
    assert rev.created_at.tzinfo is not None
    assert started <= rev.created_at <= finished


def test_history_not_rewritten_on_description_updates(session) -> None:
    route_id = save_route(session, _route(description="alpha"))
    session.commit()

    upsert_route(session, route_id, _route(description="beta"))
    session.commit()
    upsert_route(session, route_id, _route(description="gamma"))
    session.commit()

    revisions = list_route_revisions(session, route_id)
    assert [rev.revision_number for rev in revisions] == [1, 2, 3]
    assert revisions[0].after_snapshot["description"] == "alpha"
    assert revisions[1].before_snapshot is not None
    assert revisions[1].before_snapshot["description"] == "alpha"
    assert revisions[1].after_snapshot["description"] == "beta"
    assert revisions[2].before_snapshot is not None
    assert revisions[2].before_snapshot["description"] == "beta"
    assert revisions[2].after_snapshot["description"] == "gamma"
    assert revisions[0].after_snapshot["description"] == "alpha"


def test_no_op_upsert_does_not_append_revision(session) -> None:
    route_id = save_route(session, _route())
    session.commit()
    upsert_route(session, route_id, _route())
    session.commit()
    assert len(list_route_revisions(session, route_id)) == 1


def test_list_route_revisions_unknown_route_returns_empty(session) -> None:
    assert list_route_revisions(session, uuid.uuid4()) == []


def test_author_context_is_stored(session) -> None:
    route_id = save_route(
        session,
        _route(),
        author_kind="anonymous",
        author_ref="cap-token-1",
    )
    session.commit()
    rev = list_route_revisions(session, route_id)[0]
    assert rev.author_kind == "anonymous"
    assert rev.author_ref == "cap-token-1"


def test_revision_rows_are_append_only(session) -> None:
    route_id = save_route(session, _route())
    session.commit()
    revision_id = session.scalar(
        select(RouteRevisionRecord.id).where(RouteRevisionRecord.route_id == route_id)
    )
    assert revision_id is not None

    loaded = session.get(RouteRevisionRecord, revision_id)
    assert loaded is not None
    original_after = loaded.after_snapshot
    loaded.after_snapshot = {"mutated": True}
    with pytest.raises(RuntimeError, match="append-only"):
        session.commit()
    session.rollback()

    reloaded = session.get(RouteRevisionRecord, revision_id)
    assert reloaded is not None
    assert reloaded.after_snapshot == original_after
