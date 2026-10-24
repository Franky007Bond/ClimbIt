"""Failure-drill tests for injected plan-request errors."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader

from app.data.seed_routes import PUBLISHED_ALPINE_HIKE_SLUG, seed_route_id
from app.planning.plan_failure_drill import plan_failure_drill_enabled
from app.telemetry import metrics as metrics_mod

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL is unset",
)

pytest_plugins = ["tests.test_route_search"]

REPO_ROOT = Path(__file__).resolve().parents[2]
DRILL_DOC = REPO_ROOT / "_docs" / "operations" / "plan-failure-drill.md"
DRILL_EVIDENCE = (
    REPO_ROOT / "_docs" / "operations" / "evidence" / "plan-failure-drill-2026-10-24.md"
)


def test_plan_failure_drill_disabled_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CLIMBIT_PLAN_FAILURE_DRILL", "1")
    monkeypatch.setenv("CLIMBIT_ENVIRONMENT", "production")
    assert plan_failure_drill_enabled() is False


def test_plan_failure_drill_enabled_outside_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CLIMBIT_PLAN_FAILURE_DRILL", "true")
    monkeypatch.setenv("CLIMBIT_ENVIRONMENT", "local")
    assert plan_failure_drill_enabled() is True


def test_plan_failure_drill_injects_503_with_trace(
    seeded_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CLIMBIT_PLAN_FAILURE_DRILL", "1")
    monkeypatch.setenv("CLIMBIT_ENVIRONMENT", "local")
    route_id = seed_route_id(PUBLISHED_ALPINE_HIKE_SLUG)
    response = seeded_client.post(
        f"/routes/{route_id}/plans",
        json={"plan_date": "2026-07-15", "origin": "Munich"},
    )
    assert response.status_code == 503
    assert "failure drill" in response.json()["detail"].lower()
    trace_id = response.headers.get("X-Trace-Id")
    assert trace_id


def test_plan_failure_drill_records_failure_metric(
    seeded_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    metrics_mod.reset_metrics_for_tests()
    reader = InMemoryMetricReader()
    provider = MeterProvider(metric_readers=[reader])
    metrics.set_meter_provider(provider)
    metrics_mod._meter = metrics.get_meter("climbit.telemetry.test")
    metrics_mod._CONFIGURED = True
    monkeypatch.setattr(metrics_mod, "configure_metrics", lambda: None)

    monkeypatch.setenv("CLIMBIT_PLAN_FAILURE_DRILL", "1")
    monkeypatch.setenv("CLIMBIT_ENVIRONMENT", "dev")
    route_id = seed_route_id(PUBLISHED_ALPINE_HIKE_SLUG)
    response = seeded_client.post(
        f"/routes/{route_id}/plans",
        json={"plan_date": "2026-07-15", "origin": "Munich"},
    )
    assert response.status_code == 503
    reader.force_flush()
    payloads = reader.get_metrics_data()
    assert payloads is not None
    failures = 0
    for resource in payloads.resource_metrics:
        for scope in resource.scope_metrics:
            for metric in scope.metrics:
                if metric.name != "climbit.plan.requests":
                    continue
                for point in metric.data.data_points:
                    if point.attributes.get("result") == "failure":
                        failures += int(point.value)
    assert failures >= 1


def test_plan_failure_drill_documentation_and_evidence() -> None:
    doc = DRILL_DOC.read_text(encoding="utf-8")
    evidence = DRILL_EVIDENCE.read_text(encoding="utf-8")
    assert "CLIMBIT_PLAN_FAILURE_DRILL" in doc
    assert "climbit-plan-failure-rate" in doc
    assert "trace" in evidence.lower()
    assert "dashboard" in evidence.lower()
    assert "alert" in evidence.lower()
