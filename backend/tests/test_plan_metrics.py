from __future__ import annotations

import pytest
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader

from app.telemetry import metrics as metrics_mod

@pytest.fixture
def metric_reader(monkeypatch: pytest.MonkeyPatch) -> InMemoryMetricReader:
    metrics_mod._CONFIGURED = False  # noqa: SLF001
    metrics_mod._meter = None  # noqa: SLF001
    metrics_mod._http_requests = None  # noqa: SLF001
    metrics_mod._plan_requests = None  # noqa: SLF001
    metrics_mod._wiki_requests = None  # noqa: SLF001
    metrics_mod._integration_calls = None  # noqa: SLF001
    reader = InMemoryMetricReader()
    provider = MeterProvider(metric_readers=[reader])
    metrics.set_meter_provider(provider)
    metrics_mod._meter = metrics.get_meter("climbit.telemetry.test")
    metrics_mod._CONFIGURED = True
    monkeypatch.setattr(metrics_mod, "configure_metrics", lambda: None)
    yield reader
    metrics_mod._CONFIGURED = False  # noqa: SLF001


def test_http_route_template_strips_route_ids() -> None:
    path = "/routes/50620691-2211-5a6e-8dfd-1c5bf7af289b/plans"
    assert metrics_mod.http_route_template(path) == "/routes/{route_id}/plans"


def test_plan_request_counter(metric_reader: InMemoryMetricReader) -> None:
    metrics_mod.record_plan_request(status_code=200)
    metrics_mod.record_plan_request(status_code=500)
    metric_reader.force_flush()
    payloads = metric_reader.get_metrics_data()
    data_points: list[tuple[str, int]] = []
    for resource in payloads.resource_metrics:
        for scope in resource.scope_metrics:
            for metric in scope.metrics:
                if metric.name != "climbit.plan.requests":
                    continue
                for point in metric.data.data_points:
                    result = point.attributes.get("result")
                    data_points.append((str(result), int(point.value)))
    assert ("success", 1) in data_points
    assert ("failure", 1) in data_points
