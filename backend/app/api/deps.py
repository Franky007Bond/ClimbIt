from __future__ import annotations

import os
from collections.abc import Iterator

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db import create_sessionmaker


def get_db_session() -> Iterator[Session]:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise HTTPException(
            status_code=503,
            detail={"reason": "database_unavailable"},
        )
    session_factory = create_sessionmaker(database_url)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
