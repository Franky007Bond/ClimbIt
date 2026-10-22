import os
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from psycopg import sql
from sqlalchemy.exc import OperationalError

from app.db import sqlalchemy_url
from app.main import app

_SKIP_UNSET = "DATABASE_URL is unset"


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


@contextmanager
def _temporary_database(*, migrate: bool) -> Iterator[str]:
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
        if migrate:
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


def test_ready_unavailable_when_database_url_unset(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with TestClient(app) as client:
        response = client.get("/ready")
    assert response.status_code == 503
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"status": "not_ready", "reason": "database_unavailable"}


def test_ready_unavailable_when_connect_fails(monkeypatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql://climbit:climbit@127.0.0.1:5432/climbit"
    )

    def fail_connect(database_url: str):
        raise OperationalError("SELECT 1", {}, Exception("injected"))

    monkeypatch.setattr("app.health.connect_for_ready", fail_connect)
    with TestClient(app) as client:
        response = client.get("/ready")
    assert response.status_code == 503
    body = response.json()
    assert body == {"status": "not_ready", "reason": "database_unavailable"}
    raw = response.text
    assert "DATABASE_URL" not in raw
    assert "climbit" not in raw
    assert "injected" not in raw
    assert "SELECT 1" not in raw
    assert "127.0.0.1" not in raw
    assert "5432" not in raw


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason=_SKIP_UNSET)
def test_ready_at_head_when_database_url_set() -> None:
    with _temporary_database(migrate=True):
        with TestClient(app) as client:
            response = client.get("/ready")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"status": "ready"}


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason=_SKIP_UNSET)
def test_ready_migrations_pending_when_not_at_head() -> None:
    with _temporary_database(migrate=False):
        with TestClient(app) as client:
            response = client.get("/ready")
    assert response.status_code == 503
    body = response.json()
    assert body == {"status": "not_ready", "reason": "migrations_pending"}
    raw = response.text
    assert "4dcc9bd6cf18" not in raw
    assert "DATABASE_URL" not in raw
