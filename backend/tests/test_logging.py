import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager

from fastapi.testclient import TestClient

from app.json_logging import ACCESS_LOGGER_NAME, JsonFormatter
from app.main import app


class _AccessRecordHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.INFO)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@contextmanager
def _capture_access_records() -> Iterator[list[logging.LogRecord]]:
    logger = logging.getLogger(ACCESS_LOGGER_NAME)
    handler = _AccessRecordHandler()
    prior_disabled = logger.disabled
    prior_propagate = logger.propagate
    logger.disabled = False
    logger.propagate = False
    logger.addHandler(handler)
    try:
        yield handler.records
    finally:
        logger.removeHandler(handler)
        logger.disabled = prior_disabled
        logger.propagate = prior_propagate


def _access_json_lines(records: list[logging.LogRecord]) -> list[str]:
    formatter = JsonFormatter()
    lines = []
    for record in records:
        if record.name != ACCESS_LOGGER_NAME:
            continue
        if record.levelno < logging.INFO:
            continue
        lines.append(formatter.format(record))
    return lines


def test_access_logs_are_json() -> None:
    with _capture_access_records() as records:
        with TestClient(app) as client:
            openapi = client.get("/openapi.json")
            missing = client.get("/no-such-application-path")
            health = client.get("/health")
            client.get("/ready")

    assert openapi.status_code == 200
    assert missing.status_code == 404
    assert health.status_code == 200

    lines = _access_json_lines(records)
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


def test_access_logs_omit_secrets_and_query_string() -> None:
    with _capture_access_records() as records:
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

    raw = "\n".join(_access_json_lines(records))
    assert "secret-token" not in raw
    assert "example.invalid" not in raw
    assert "session=abc" not in raw
    assert "leak" not in raw
    assert "token=" not in raw
    assert "DATABASE_URL" not in raw
    for line in _access_json_lines(records):
        payload = json.loads(line)
        if payload.get("path") == "/openapi.json":
            assert "?" not in payload["path"]
            assert payload["method"] == "GET"
