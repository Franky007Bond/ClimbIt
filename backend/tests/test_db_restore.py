"""Restore-drill test: backup and restore against disposable databases."""

from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path

import pytest
from alembic import command
from psycopg import sql
from sqlalchemy import text

from app.data.seed_routes import PUBLISHED_ALPINE_HIKE_SLUG, seed_route_id
from app.db import create_sessionmaker
from app.db_backup import backup_database, restore_database
from app.seed import seed
from tests.test_migrations import (
    _alembic_config,
    _connect,
    _database_exists,
    _operator_url,
)

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL")
    or shutil.which("pg_dump") is None
    or shutil.which("pg_restore") is None,
    reason="DATABASE_URL unset or pg_dump/pg_restore not on PATH",
)


@pytest.fixture
def restore_drill_databases() -> tuple[str, str]:
    admin_url = os.environ["DATABASE_URL"]
    source_db = f"test_{uuid.uuid4().hex}"
    target_db = f"test_{uuid.uuid4().hex}"
    assert source_db.startswith("test_") and target_db.startswith("test_")

    with _connect(admin_url) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(source_db)))

    os.environ["DATABASE_URL"] = _operator_url(source_db)
    try:
        command.upgrade(_alembic_config(), "head")
        Session = create_sessionmaker(_operator_url(source_db))
        with Session() as session:
            seed(session)
            session.commit()
        yield source_db, target_db
    finally:
        os.environ["DATABASE_URL"] = admin_url
        with _connect(admin_url) as conn:
            for name in (source_db, target_db):
                conn.execute(
                    sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(
                        sql.Identifier(name)
                    )
                )


def test_restore_drill_round_trip(
    restore_drill_databases: tuple[str, str], tmp_path: Path
) -> None:
    source_db, target_db = restore_drill_databases
    admin_url = os.environ["DATABASE_URL"]
    source_url = _operator_url(source_db)

    expected_route_id = seed_route_id(PUBLISHED_ALPINE_HIKE_SLUG)
    Session = create_sessionmaker(source_url)
    with Session() as session:
        before = session.execute(text("SELECT count(*) FROM routes")).scalar_one()
        assert before >= 1

    dump_path = tmp_path / "climbit-restore-drill.dump"
    backup_database(source_url, dump_path)
    assert dump_path.stat().st_size > 0

    restore_database(admin_url, target_db, dump_path)

    restored_url = _operator_url(target_db)
    Session = create_sessionmaker(restored_url)
    with Session() as session:
        after = session.execute(text("SELECT count(*) FROM routes")).scalar_one()
        assert after == before
        row = session.execute(
            text("SELECT id FROM routes WHERE id = :id"),
            {"id": expected_route_id},
        ).one_or_none()
        assert row is not None

    assert _database_exists(admin_url, target_db)
