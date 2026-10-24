import os
from typing import Any

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine
from sqlalchemy.exc import InterfaceError, OperationalError
from sqlalchemy.pool import NullPool

from app.db import sqlalchemy_url

_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CONNECT_TIMEOUT_SECONDS = 2


def _alembic_config() -> Config:
    return Config(os.path.join(_BACKEND_ROOT, "alembic.ini"))


def connect_for_ready(database_url: str):
    url = sqlalchemy_url(database_url)
    return create_engine(
        url,
        poolclass=NullPool,
        connect_args={"connect_timeout": _CONNECT_TIMEOUT_SECONDS},
    )


def _unavailable() -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"status": "not_ready", "reason": "database_unavailable"},
    )


def _migrations_pending() -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"status": "not_ready", "reason": "migrations_pending"},
    )


def ready_response() -> JSONResponse:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        return _unavailable()

    engine = None
    try:
        engine = connect_for_ready(database_url)
        with engine.connect() as connection:
            try:
                script = ScriptDirectory.from_config(_alembic_config())
                heads = set(script.get_heads())
                current = set(
                    MigrationContext.configure(connection).get_current_heads()
                )
            except OperationalError, InterfaceError, OSError, TimeoutError:
                return _unavailable()
            except Exception:
                return _migrations_pending()
            if not heads or current != heads:
                return _migrations_pending()
            return JSONResponse(content={"status": "ready"})
    except Exception:
        return _unavailable()
    finally:
        if engine is not None:
            engine.dispose()


def health_body() -> dict[str, Any]:
    return {"status": "ok"}
