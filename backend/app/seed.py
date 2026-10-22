from __future__ import annotations

import os
import sys
import uuid

from sqlalchemy.orm import Session

from app.data.seed_routes import build_seed_routes
from app.db import create_sessionmaker
from app.repositories.routes import upsert_route


def seed(session: Session) -> list[uuid.UUID]:
    route_ids: list[uuid.UUID] = []
    for route_id, route in build_seed_routes():
        route_ids.append(upsert_route(session, route_id, route))
    return route_ids


def main() -> int:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        return 1
    SessionLocal = create_sessionmaker(database_url)
    session = SessionLocal()
    bind = session.get_bind()
    try:
        seed(session)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        bind.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(main())
