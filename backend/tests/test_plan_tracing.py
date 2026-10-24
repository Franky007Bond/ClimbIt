from __future__ import annotations

import json
import logging
import os

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app.data.seed_routes import PUBLISHED_ALPINE_HIKE_SLUG
from app.data.seed_routes import seed_route_id
from app.json_logging import ACCESS_LOGGER_NAME, JsonFormatter, PLANNING_LOGGER_NAME
from app.telemetry import tracing as tracing_mod

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL is unset",
)

pytest_plugins = ["tests.test_route_search"]

EXPECTED_STEP_SPANS = {
    "plan.build",
    "planning.weather",
    "planning.avalanche",
    "planning.transit",
    "planning.gear",
    "planning.recommendation",
    "planning.database",
}


@pytest.fixture
def memory_span_exporter(monkeypatch: pytest.MonkeyPatch) -> InMemorySpanExporter:
    tracing_mod.reset_tracing_for_tests()
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracing_mod.install_tracer_provider(provider)
    monkeypatch.setattr(tracing_mod, "configure_tracing", lambda: None)
    yield exporter
    provider.force_flush()
    exporter.shutdown()
    tracing_mod.reset_tracing_for_tests()


def _json_log_lines(caplog, logger_name: str) -> list[dict[str, object]]:
    formatter = JsonFormatter()
    lines: list[dict[str, object]] = []
    for record in caplog.records:
        if record.name != logger_name:
            continue
        if record.levelno < logging.INFO:
            continue
        lines.append(json.loads(formatter.format(record)))
    return lines


@pytest.fixture
def traced_seeded_client(
    memory_span_exporter: InMemorySpanExporter,
    seeded_client,
):
    del memory_span_exporter
    return seeded_client


def test_plan_response_trace_id_matches_logs_and_spans(
    traced_seeded_client,
    memory_span_exporter: InMemorySpanExporter,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    caplog.set_level(logging.INFO, logger=PLANNING_LOGGER_NAME)
    caplog.set_level(logging.INFO, logger=ACCESS_LOGGER_NAME)
    route_id = seed_route_id(PUBLISHED_ALPINE_HIKE_SLUG)
    response = traced_seeded_client.post(
        f"/routes/{route_id}/plans",
        json={"plan_date": "2026-07-15", "origin": "Munich Hauptbahnhof"},
    )
    assert response.status_code == 200
    body = response.json()
    trace_id = body.get("trace_id")
    assert isinstance(trace_id, str)
    assert len(trace_id) == 32
    assert trace_id.islower()

    access_logs = _json_log_lines(caplog, ACCESS_LOGGER_NAME)
    planning_logs = _json_log_lines(caplog, PLANNING_LOGGER_NAME)
    assert any(line.get("trace_id") == trace_id for line in access_logs)
    if planning_logs:
        assert any(line.get("trace_id") == trace_id for line in planning_logs)

    provider = trace.get_tracer_provider()
    if hasattr(provider, "force_flush"):
        provider.force_flush()
    span_names = {span.name for span in memory_span_exporter.get_finished_spans()}
    assert EXPECTED_STEP_SPANS <= span_names
