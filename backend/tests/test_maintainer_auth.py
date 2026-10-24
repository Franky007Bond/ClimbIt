import json
import logging

import bcrypt
import pytest
from fastapi.testclient import TestClient

from app.main import app

TEST_USERNAME = "operator"
TEST_PASSWORD = "test-password"
TEST_HASH = bcrypt.hashpw(
    TEST_PASSWORD.encode("utf-8"), bcrypt.gensalt(rounds=4)
).decode()


@pytest.fixture(autouse=True)
def maintainer_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAINTAINER_SESSION_SECRET", "test-maintainer-secret")
    monkeypatch.setenv(
        "MAINTAINER_ALLOWLIST",
        json.dumps([{"username": TEST_USERNAME, "password_bcrypt": TEST_HASH}]),
    )


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_successful_login_sets_session_cookie(client: TestClient) -> None:
    response = client.post(
        "/maintainer/sessions",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200
    assert response.json() == {"username": TEST_USERNAME}
    assert "climbit_maintainer_session" in response.cookies


def test_unknown_user_rejected(client: TestClient) -> None:
    response = client.post(
        "/maintainer/sessions",
        json={"username": "unknown", "password": TEST_PASSWORD},
    )
    assert response.status_code == 401
    assert "climbit_maintainer_session" not in response.cookies


def test_wrong_password_rejected(client: TestClient) -> None:
    response = client.post(
        "/maintainer/sessions",
        json={"username": TEST_USERNAME, "password": "wrong-password"},
    )
    assert response.status_code == 401
    assert "climbit_maintainer_session" not in response.cookies


def test_session_endpoint_requires_cookie(client: TestClient) -> None:
    response = client.get("/maintainer/session")
    assert response.status_code == 401


def test_session_endpoint_returns_username_after_login(client: TestClient) -> None:
    login = client.post(
        "/maintainer/sessions",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )
    assert login.status_code == 200
    session = client.get("/maintainer/session")
    assert session.status_code == 200
    assert session.json() == {"username": TEST_USERNAME}


def test_failed_login_does_not_log_password(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)
    response = client.post(
        "/maintainer/sessions",
        json={"username": TEST_USERNAME, "password": "wrong-password-value"},
    )
    assert response.status_code == 401
    logged = "\n".join(record.getMessage() for record in caplog.records)
    assert "wrong-password-value" not in logged
    assert TEST_PASSWORD not in logged
