import json
import logging
import os

import bcrypt
import pytest
from fastapi.testclient import TestClient

from app.db import create_sessionmaker
from app.json_logging import ACCESS_LOGGER_NAME, JsonFormatter
from app.main import app
from app.repositories.trip_capabilities import count_active_trip_capabilities
from app.trip_auth import TRIP_CAPABILITY_COOKIE_NAME
from tests.test_route_search import _operator_url

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL is unset",
)

pytest_plugins = ["tests.test_route_search"]


@pytest.fixture(autouse=True)
def trip_capability_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRIP_CAPABILITY_SECRET", "test-trip-capability-secret")


@pytest.fixture
def maintainer_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAINTAINER_SESSION_SECRET", "test-maintainer-secret")
    password_hash = bcrypt.hashpw(b"test-password", bcrypt.gensalt(rounds=4)).decode()
    monkeypatch.setenv(
        "MAINTAINER_ALLOWLIST",
        json.dumps([{"username": "operator", "password_bcrypt": password_hash}]),
    )


def _access_json_lines(caplog) -> list[str]:
    formatter = JsonFormatter()
    lines = []
    for record in caplog.records:
        if record.name != ACCESS_LOGGER_NAME:
            continue
        if record.levelno < logging.INFO:
            continue
        lines.append(formatter.format(record))
    return lines


def test_unconfigured_secret_returns_503(
    monkeypatch: pytest.MonkeyPatch,
    migrated_test_database: str,
) -> None:
    monkeypatch.delenv("TRIP_CAPABILITY_SECRET", raising=False)
    with TestClient(app) as client:
        response = client.get("/trips/capability")
    assert response.status_code == 503
    assert response.json()["detail"]["reason"] == "trip_capability_unconfigured"
    assert TRIP_CAPABILITY_COOKIE_NAME not in response.cookies


def test_first_request_sets_http_only_cookie(
    migrated_test_database: str,
) -> None:
    with TestClient(app) as client:
        response = client.get("/trips/capability")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
    token = response.cookies.get(TRIP_CAPABILITY_COOKIE_NAME)
    assert token
    assert token not in response.text
    Session = create_sessionmaker(_operator_url(migrated_test_database))
    with Session() as session:
        assert count_active_trip_capabilities(session) == 1


def test_repeat_request_does_not_rotate_cookie(
    migrated_test_database: str,
) -> None:
    with TestClient(app) as client:
        first = client.get("/trips/capability")
        first_token = client.cookies[TRIP_CAPABILITY_COOKIE_NAME]
        second = client.get("/trips/capability")
        second_token = client.cookies[TRIP_CAPABILITY_COOKIE_NAME]
    assert first.status_code == 200
    assert second.status_code == 200
    assert first_token == second_token
    assert "set-cookie" not in {header.lower() for header in second.headers}
    Session = create_sessionmaker(_operator_url(migrated_test_database))
    with Session() as session:
        assert count_active_trip_capabilities(session) == 1


def test_invalid_cookie_issues_new_capability(
    migrated_test_database: str,
) -> None:
    with TestClient(app) as client:
        client.cookies.set(TRIP_CAPABILITY_COOKIE_NAME, "not-a-valid-token")
        response = client.get("/trips/capability")
    assert response.status_code == 200
    new_token = response.cookies.get(TRIP_CAPABILITY_COOKIE_NAME)
    assert new_token
    assert new_token != "not-a-valid-token"


def test_delete_invalidates_and_clears_cookie(
    migrated_test_database: str,
) -> None:
    with TestClient(app) as client:
        issued = client.get("/trips/capability")
        old_token = issued.cookies[TRIP_CAPABILITY_COOKIE_NAME]
        deleted = client.delete("/trips/capability")
        assert deleted.status_code == 204
        assert TRIP_CAPABILITY_COOKIE_NAME not in deleted.cookies or not deleted.cookies.get(
            TRIP_CAPABILITY_COOKIE_NAME
        )
        stale = client.get("/trips/capability")
    assert stale.status_code == 200
    new_token = stale.cookies[TRIP_CAPABILITY_COOKIE_NAME]
    assert new_token != old_token


def test_delete_without_cookie_returns_401(migrated_test_database: str) -> None:
    with TestClient(app) as client:
        response = client.delete("/trips/capability")
    assert response.status_code == 401


def test_capability_absent_from_access_logs(
    migrated_test_database: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    with TestClient(app) as client:
        response = client.get(
            "/trips/capability?token=leak",
            headers={"Cookie": f"{TRIP_CAPABILITY_COOKIE_NAME}=should-not-log"},
        )
    assert response.status_code == 200
    token = response.cookies[TRIP_CAPABILITY_COOKIE_NAME]
    raw = "\n".join(_access_json_lines(caplog))
    assert token not in raw
    assert "should-not-log" not in raw
    assert "leak" not in raw
    for line in _access_json_lines(caplog):
        payload = json.loads(line)
        if payload.get("path") == "/trips/capability":
            assert "?" not in payload["path"]


def test_maintainer_session_unaffected(
    migrated_test_database: str,
    maintainer_env: None,
) -> None:
    with TestClient(app) as client:
        trip = client.get("/trips/capability")
        login = client.post(
            "/maintainer/sessions",
            json={"username": "operator", "password": "test-password"},
        )
        assert trip.status_code == 200
        assert login.status_code == 200
        assert TRIP_CAPABILITY_COOKIE_NAME in trip.cookies
        assert "climbit_maintainer_session" in login.cookies
