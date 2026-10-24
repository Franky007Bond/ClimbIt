from __future__ import annotations

import os
import re
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.data.seed_routes import PUBLISHED_ALPINE_HIKE_SLUG
from app.data.seed_routes import seed_route_id
from app.main import app
from app.security.free_text import sanitize_free_text
from app.security.outbound import assert_allowed_outbound_url

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_APP = REPO_ROOT / "backend" / "app"

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL is unset",
)

pytest_plugins = ["tests.test_route_search"]


def test_sanitize_free_text_strips_markup_and_control_chars() -> None:
    raw = "  Hello<script>alert(1)</script>\x00world  "
    assert sanitize_free_text(raw) == "Helloscriptalert(1)/scriptworld"


def test_wiki_description_is_stored_sanitized(
    seeded_client: TestClient,
    migrated_test_database: str,
) -> None:
    from app.db import create_sessionmaker
    from app.repositories.routes import current_applied_revision_number
    from tests.test_route_search import _operator_url

    route_id = seed_route_id(PUBLISHED_ALPINE_HIKE_SLUG)
    Session = create_sessionmaker(_operator_url(migrated_test_database))
    with Session() as session:
        base = current_applied_revision_number(session, route_id)
    assert base is not None
    payload = "<b>Steep</b> section\x07 near the ridge."
    response = seeded_client.patch(
        f"/routes/{route_id}/descriptive",
        json={"base_revision_number": base, "description": payload},
    )
    assert response.status_code == 200
    assert response.json()["description"] == sanitize_free_text(payload)
    detail = seeded_client.get(f"/routes/{route_id}").json()
    assert detail["description"] == sanitize_free_text(payload)


def test_outbound_guard_rejects_user_supplied_hosts() -> None:
    with pytest.raises(ValueError, match="not an allowed integration host"):
        assert_allowed_outbound_url("https://evil.example.invalid/plan")


def test_gpx_external_link_does_not_fetch_urls(seeded_client: TestClient) -> None:
    from tests.test_gpx_upload import _post_gpx, _read_fixture

    with patch("urllib.request.urlopen") as urlopen:
        response = _post_gpx(seeded_client, _read_fixture("external_link.gpx"))
    assert response.status_code == 201
    urlopen.assert_not_called()


def test_repository_modules_avoid_interpolated_sql() -> None:
    repo_dir = BACKEND_APP / "repositories"
    patterns = (
        re.compile(r"\.execute\s*\(\s*f['\"]"),
        re.compile(r"\.execute\s*\(\s*['\"].*\{"),
        re.compile(r"text\s*\(\s*f['\"]"),
    )
    offenders: list[str] = []
    for path in repo_dir.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        for pattern in patterns:
            if pattern.search(source):
                offenders.append(f"{path.name}: {pattern.pattern}")
    assert not offenders, offenders


def test_threat_model_covers_accepted_wiki_vandalism() -> None:
    doc = (REPO_ROOT / "_docs" / "security" / "threat-model.md").read_text(
        encoding="utf-8"
    )
    lowered = doc.lower()
    assert "wiki vandalism" in lowered
    assert "accepted risk" in lowered
    assert "abuse case" in lowered or "abuse cases" in lowered


def test_health_and_ready_responses_exclude_env_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql://climbit:top-secret@db:5432/climbit"
    )
    monkeypatch.setenv("TRIP_CAPABILITY_SECRET", "trip-secret-value")
    with TestClient(app) as client:
        health = client.get("/health")
        ready = client.get("/ready")
    assert health.status_code == 200
    assert ready.status_code in {200, 503}
    raw = health.text + ready.text
    assert "top-secret" not in raw
    assert "trip-secret-value" not in raw
    assert "DATABASE_URL" not in raw
