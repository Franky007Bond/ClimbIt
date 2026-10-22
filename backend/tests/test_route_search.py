import os
import uuid
from collections.abc import Iterator

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from psycopg import sql
from sqlalchemy import text

from app.data.seed_routes import PUBLISHED_ALPINE_HIKE_SLUG
from app.data.seed_routes import PUBLISHED_KLETTERSTEIG_SLUG
from app.data.seed_routes import PUBLISHED_OUTDOOR_CLIMBING_SLUG
from app.data.seed_routes import seed_route_id
from app.db import create_sessionmaker
from app.db import sqlalchemy_url
from app.main import app
from app.seed import seed

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
def seeded_client(migrated_test_database: str) -> Iterator[TestClient]:
    Session = create_sessionmaker(_operator_url(migrated_test_database))
    with Session() as session:
        seed(session)
        session.commit()
    with TestClient(app) as client:
        yield client


def test_default_search_lists_only_published_routes(seeded_client: TestClient) -> None:
    response = seeded_client.get("/routes")
    assert response.status_code == 200
    body = response.json()
    assert len(body["routes"]) == 3
    names = {item["name"] for item in body["routes"]}
    assert "Seed Quarantined Klettersteig" not in names
    publications = {item["publication"] for item in body["routes"]}
    assert publications == {"published"}


def test_search_includes_route_state_and_region_coverage(seeded_client: TestClient) -> None:
    response = seeded_client.get("/routes")
    assert response.status_code == 200
    alpine = next(
        item
        for item in response.json()["routes"]
        if item["id"] == str(seed_route_id(PUBLISHED_ALPINE_HIKE_SLUG))
    )
    assert alpine["provenance"] == "seed"
    assert alpine["completeness"] == "complete"
    assert alpine["assessment"] == "unassessed"
    assert alpine["region"]["coverage"] == "sample"
    assert alpine["region"]["name"] == "Chamonix"
    assert alpine["region"]["country"] == "FR"
    trailhead = alpine["trailhead"]
    assert trailhead is not None
    assert "longitude" in trailhead and "latitude" in trailhead


def test_search_region_filter_requires_exact_spelling_and_casing(
    seeded_client: TestClient,
) -> None:
    matching = seeded_client.get("/routes", params={"region": "Allgäu"})
    assert matching.status_code == 200
    assert len(matching.json()["routes"]) == 2

    wrong_casing = seeded_client.get("/routes", params={"region": "allgäu"})
    assert wrong_casing.status_code == 200
    assert wrong_casing.json()["routes"] == []


def test_search_rejects_lowercase_country_code(seeded_client: TestClient) -> None:
    response = seeded_client.get("/routes", params={"country": "de"})
    assert response.status_code == 422
    assert "country" in response.json()["detail"].lower()


def test_search_rejects_unknown_difficulty_scale(seeded_client: TestClient) -> None:
    response = seeded_client.get(
        "/routes",
        params={
            "route_type": "klettersteig",
            "difficulty_scale": "not_a_real_scale",
        },
    )
    assert response.status_code == 422
    assert "difficulty_scale" in response.json()["detail"]


def test_search_rejects_difficulty_min_harder_than_max(seeded_client: TestClient) -> None:
    response = seeded_client.get(
        "/routes",
        params={
            "route_type": "klettersteig",
            "difficulty_scale": "k1_k6",
            "difficulty_min": "K5",
            "difficulty_max": "K2",
        },
    )
    assert response.status_code == 422
    assert "difficulty_min" in response.json()["detail"]


def test_search_filters_by_region_country_route_type_and_duration(
    seeded_client: TestClient,
) -> None:
    response = seeded_client.get(
        "/routes",
        params={
            "region": "Allgäu",
            "country": "DE",
            "route_type": "klettersteig",
            "duration_min_minutes": 120,
            "duration_max_minutes": 200,
        },
    )
    assert response.status_code == 200
    routes = response.json()["routes"]
    assert len(routes) == 1
    assert routes[0]["id"] == str(seed_route_id(PUBLISHED_KLETTERSTEIG_SLUG))


def test_search_rejects_difficulty_scale_for_wrong_route_type(
    seeded_client: TestClient,
) -> None:
    response = seeded_client.get(
        "/routes",
        params={
            "route_type": "alpine_hike",
            "difficulty_scale": "k1_k6",
            "difficulty_min": "K3",
        },
    )
    assert response.status_code == 422
    assert "route_type" in response.json()["detail"]


def test_search_filters_by_difficulty_scale_and_bounds(seeded_client: TestClient) -> None:
    response = seeded_client.get(
        "/routes",
        params={
            "route_type": "outdoor_climbing",
            "difficulty_scale": "French",
            "difficulty_min": "6a",
            "difficulty_max": "6a",
        },
    )
    assert response.status_code == 200
    routes = response.json()["routes"]
    assert len(routes) == 1
    assert routes[0]["id"] == str(seed_route_id(PUBLISHED_OUTDOOR_CLIMBING_SLUG))


def test_search_filters_by_season_month_and_transit(migrated_test_database: str) -> None:
    Session = create_sessionmaker(_operator_url(migrated_test_database))
    route_id = seed_route_id(PUBLISHED_KLETTERSTEIG_SLUG)
    with Session() as session:
        seed(session)
        session.execute(
            text(
                """
                UPDATE routes
                SET season_months = CAST(:months AS jsonb),
                    transit_accessibility = :transit
                WHERE id = :id
                """
            ),
            {
                "months": "[6, 7, 8]",
                "transit": "transit_friendly",
                "id": route_id,
            },
        )
        session.commit()

    with TestClient(app) as client:
        response = client.get(
            "/routes",
            params={"season_month": 7, "transit_accessibility": "transit_friendly"},
        )
    assert response.status_code == 200
    routes = response.json()["routes"]
    assert len(routes) == 1
    assert routes[0]["id"] == str(route_id)


def test_routes_search_unavailable_without_database_url(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with TestClient(app) as client:
        response = client.get("/routes")
    assert response.status_code == 503
