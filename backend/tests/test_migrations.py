import os
import uuid
from collections.abc import Iterator

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from psycopg import sql
from sqlalchemy import create_engine
from sqlalchemy import text

from app.db import sqlalchemy_url

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


def test_upgrade_head_enables_postgis_on_fresh_database(
    migrated_test_database: str,
) -> None:
    script = ScriptDirectory.from_config(_alembic_config())
    heads = script.get_heads()
    assert len(heads) == 1
    head = heads[0]

    engine = create_engine(sqlalchemy_url(_operator_url(migrated_test_database)))
    try:
        with engine.connect() as connection:
            current = MigrationContext.configure(connection).get_current_heads()
            assert current == (head,)
            connection.execute(text("SELECT PostGIS_Version()"))
    finally:
        engine.dispose()
