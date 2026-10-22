import json
import logging

from fastapi.testclient import TestClient

from app.json_logging import ACCESS_LOGGER_NAME, JsonFormatter
from app.main import app


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


def test_access_logs_are_json(caplog) -> None:
    caplog.set_level(logging.INFO)
    with TestClient(app) as client:
        openapi = client.get("/openapi.json")
        missing = client.get("/no-such-application-path")
        health = client.get("/health")
        client.get("/ready")

    assert openapi.status_code == 200
    assert missing.status_code == 404
    assert health.status_code == 200

    lines = _access_json_lines(caplog)
    parsed = [json.loads(line) for line in lines]
    openapi_logs = [
        item
        for item in parsed
        if item.get("method") == "GET" and item.get("path") == "/openapi.json"
    ]
    assert openapi_logs
    assert openapi_logs[0]["status_code"] == 200

    missing_logs = [
        item
        for item in parsed
        if item.get("path") == "/no-such-application-path"
    ]
    assert missing_logs
    assert missing_logs[0]["status_code"] == 404

    probe_paths = {item.get("path") for item in parsed}
    assert "/health" not in probe_paths
    assert "/ready" not in probe_paths


def test_access_logs_omit_secrets_and_query_string(caplog) -> None:
    caplog.set_level(logging.INFO)
    with TestClient(app) as client:
        response = client.get(
            "/openapi.json?token=leak",
            headers={
                "Authorization": "Bearer secret-token",
                "Origin": "https://example.invalid",
                "Cookie": "session=abc",
            },
        )
    assert response.status_code == 200

    raw = "\n".join(_access_json_lines(caplog))
    assert "secret-token" not in raw
    assert "example.invalid" not in raw
    assert "session=abc" not in raw
    assert "leak" not in raw
    assert "token=" not in raw
    assert "DATABASE_URL" not in raw
    for line in _access_json_lines(caplog):
        payload = json.loads(line)
        if payload.get("path") == "/openapi.json":
            assert "?" not in payload["path"]
            assert payload["method"] == "GET"
