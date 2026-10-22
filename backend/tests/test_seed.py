import os
import uuid
from collections.abc import Iterator

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from psycopg import sql
from sqlalchemy import text

from app.data.seed_routes import PUBLISHED_ALPINE_HIKE_SLUG
from app.data.seed_routes import PUBLISHED_KLETTERSTEIG_SLUG
from app.data.seed_routes import PUBLISHED_OUTDOOR_CLIMBING_SLUG
from app.data.seed_routes import QUARANTINED_ALPINE_HIKE_SLUG
from app.data.seed_routes import QUARANTINED_KLETTERSTEIG_SLUG
from app.data.seed_routes import QUARANTINED_OUTDOOR_CLIMBING_SLUG
from app.data.seed_routes import SEED_NAMESPACE
from app.data.seed_routes import SEED_SLUGS
from app.data.seed_routes import build_seed_routes
from app.data.seed_routes import seed_route_id
from app.db import create_sessionmaker
from app.db import sqlalchemy_url
from app.domain.route import Publication
from app.domain.route import Provenance
from app.domain.route import RegionCoverage
from app.domain.route import RouteType
from app.repositories.routes import get_route
from app.repositories.routes import save_route
from app.seed import seed

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL is unset",
)

EXPECTED_SEED_IDS = {
    PUBLISHED_KLETTERSTEIG_SLUG: uuid.UUID("0752512e-a99e-536a-8615-f5da14ce3aee"),
    PUBLISHED_ALPINE_HIKE_SLUG: uuid.UUID("50620691-2211-5a6e-8dfd-1c5bf7af289b"),
    PUBLISHED_OUTDOOR_CLIMBING_SLUG: uuid.UUID("3348fe91-e057-5e17-8cdf-ce8e1443f759"),
    QUARANTINED_KLETTERSTEIG_SLUG: uuid.UUID("b27a3ca0-e679-5625-bb2c-46e4862a44a4"),
    QUARANTINED_ALPINE_HIKE_SLUG: uuid.UUID("ba5221a5-db02-58c7-a4af-189a9381d3fd"),
    QUARANTINED_OUTDOOR_CLIMBING_SLUG: uuid.UUID("4118b2d0-b41d-58f6-a1ad-43d860a5445e"),
}


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


def _route_count(session) -> int:
    return session.execute(text("SELECT count(*) FROM routes")).scalar_one()


def _seed_ids() -> list[uuid.UUID]:
    return [seed_route_id(slug) for slug in SEED_SLUGS]


def test_seed_uuid_v5_matches_issue_values() -> None:
    assert SEED_NAMESPACE == uuid.UUID("00000000-0000-4000-8000-000000000010")
    for slug, expected in EXPECTED_SEED_IDS.items():
        assert uuid.uuid5(SEED_NAMESPACE, slug) == expected
        assert seed_route_id(slug) == expected


def test_seed_twice_then_preserves_seventh_row(session) -> None:
    fixtures = dict(build_seed_routes())
    seed(session)
    session.commit()
    assert _route_count(session) == 6

    mutated_id = EXPECTED_SEED_IDS[PUBLISHED_KLETTERSTEIG_SLUG]
    session.execute(
        text("UPDATE routes SET name = :name WHERE id = :id"),
        {"name": "locally edited seed name", "id": mutated_id},
    )
    session.commit()

    seed(session)
    session.commit()
    assert _route_count(session) == 6
    restored = get_route(session, mutated_id)
    assert restored is not None
    assert restored.name == fixtures[mutated_id].name

    extra = fixtures[mutated_id].model_copy(update={"name": "Operator extra route"})
    seventh_id = save_route(session, extra)
    session.commit()
    assert seventh_id not in EXPECTED_SEED_IDS.values()

    seed(session)
    session.commit()
    assert _route_count(session) == 7
    assert get_route(session, seventh_id) is not None
    remaining = session.execute(text("SELECT id FROM routes")).scalars().all()
    assert set(remaining) == set(_seed_ids()) | {seventh_id}

    for route_id, expected in fixtures.items():
        loaded = get_route(session, route_id)
        assert loaded is not None
        assert loaded.name == expected.name
        assert loaded.publication is expected.publication
        assert loaded.region.coverage is expected.region.coverage
        assert loaded.duration_is_estimated is True
        assert loaded.provenance is Provenance.SEED
        assert loaded.closure_assessment is None


def test_seed_row_contents(session) -> None:
    fixtures = dict(build_seed_routes())
    seed(session)
    session.commit()

    closure_statuses = session.execute(
        text("SELECT closure_status FROM routes")
    ).scalars().all()
    assert closure_statuses == [None] * 6

    estimated_flags = session.execute(
        text("SELECT duration_is_estimated FROM routes")
    ).scalars().all()
    assert estimated_flags == [True] * 6

    published = get_route(session, EXPECTED_SEED_IDS[PUBLISHED_KLETTERSTEIG_SLUG])
    assert published is not None
    assert published.route_type is RouteType.KLETTERSTEIG
    assert published.publication is Publication.PUBLISHED
    assert published.region.name == "Allgäu"
    assert published.region.country == "DE"
    assert published.region.coverage is RegionCoverage.SUPPORTED
    assert published.trailhead is not None
    assert published.linestring is not None
    assert len(published.linestring.points) >= 2
    assert published.elevation_min_m is not None
    assert published.elevation_max_m is not None
    assert published.elevation_max_m >= published.elevation_min_m
    assert published.duration_minutes is not None
    assert published.duration_minutes > 0
    assert published.approach_minutes is not None
    assert published.technical_minutes is not None
    assert published.descent_minutes is not None
    assert published.approach_minutes > 0
    assert published.technical_minutes > 0
    assert published.descent_minutes > 0
    assert published.duration_minutes == (
        published.approach_minutes
        + published.technical_minutes
        + published.descent_minutes
    )
    assert published.difficulty == fixtures[
        EXPECTED_SEED_IDS[PUBLISHED_KLETTERSTEIG_SLUG]
    ].difficulty

    alpine = get_route(session, EXPECTED_SEED_IDS[PUBLISHED_ALPINE_HIKE_SLUG])
    assert alpine is not None
    assert alpine.route_type is RouteType.ALPINE_HIKE
    assert alpine.publication is Publication.PUBLISHED
    assert alpine.region.name == "Chamonix"
    assert alpine.region.country == "FR"
    assert alpine.region.coverage is RegionCoverage.SAMPLE
    assert alpine.trailhead is not None
    assert alpine.linestring is not None
    assert alpine.duration_minutes is not None
    assert alpine.difficulty == fixtures[
        EXPECTED_SEED_IDS[PUBLISHED_ALPINE_HIKE_SLUG]
    ].difficulty

    outdoor = get_route(session, EXPECTED_SEED_IDS[PUBLISHED_OUTDOOR_CLIMBING_SLUG])
    assert outdoor is not None
    assert outdoor.route_type is RouteType.OUTDOOR_CLIMBING
    assert outdoor.publication is Publication.PUBLISHED
    assert outdoor.region.coverage is RegionCoverage.SUPPORTED
    assert outdoor.difficulty == fixtures[
        EXPECTED_SEED_IDS[PUBLISHED_OUTDOOR_CLIMBING_SLUG]
    ].difficulty

    for slug in (
        QUARANTINED_KLETTERSTEIG_SLUG,
        QUARANTINED_ALPINE_HIKE_SLUG,
        QUARANTINED_OUTDOOR_CLIMBING_SLUG,
    ):
        loaded = get_route(session, EXPECTED_SEED_IDS[slug])
        assert loaded is not None
        assert loaded.publication is Publication.QUARANTINED
        assert loaded.trailhead is None
        assert loaded.linestring is None
        assert loaded.elevation_min_m is None
        assert loaded.elevation_max_m is None
        assert loaded.duration_minutes is None
        assert loaded.duration_is_estimated is True
        assert loaded.closure_assessment is None
        assert loaded.provenance is Provenance.SEED


def test_save_route_still_assigns_new_uuid(session) -> None:
    fixtures = dict(build_seed_routes())
    sample = next(iter(fixtures.values()))
    first = save_route(session, sample)
    second = save_route(session, sample)
    session.commit()
    assert first != second
    assert first not in EXPECTED_SEED_IDS.values()
    assert second not in EXPECTED_SEED_IDS.values()
