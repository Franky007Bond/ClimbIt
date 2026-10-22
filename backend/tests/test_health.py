from fastapi.testclient import TestClient

from app.main import app


def test_health_ok_json_without_database(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    def fail_connect(*args, **kwargs):
        raise AssertionError("health must not open a database connection")

    monkeypatch.setattr("app.health.connect_for_ready", fail_connect)
    monkeypatch.setattr("app.health.create_engine", fail_connect)

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"status": "ok"}


def test_health_ok_with_invalid_database_url(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgres://invalid")
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_body_has_no_secrets(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://climbit:secret@db-host:5432/climbit")
    with TestClient(app) as client:
        response = client.get("/health")
    raw = response.text
    assert "DATABASE_URL" not in raw
    assert "secret" not in raw
    assert "db-host" not in raw
    assert "5432" not in raw
    assert response.json() == {"status": "ok"}
