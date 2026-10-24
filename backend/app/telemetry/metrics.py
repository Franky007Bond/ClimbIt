from __future__ import annotations

import os
import re

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.metrics import Counter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource

_CONFIGURED = False
_meter: metrics.Meter | None = None
_http_requests: Counter | None = None
_plan_requests: Counter | None = None
_wiki_requests: Counter | None = None
_integration_calls: Counter | None = None

_ROUTE_ID = re.compile(
    r"^/routes/[0-9a-fA-F-]{36}(/descriptive|/protected-edits|/plans)?$"
)


def _service_resource() -> Resource:
    service_name = os.environ.get("OTEL_SERVICE_NAME", "climbit-api").strip() or "climbit-api"
    service_version = os.environ.get("OTEL_SERVICE_VERSION", "dev").strip() or "dev"
    environment = os.environ.get("CLIMBIT_ENVIRONMENT", "local").strip() or "local"
    return Resource.create(
        {
            "service.name": service_name,
            "service.version": service_version,
            "deployment.environment": environment,
        }
    )


def reset_metrics_for_tests() -> None:
    """Allow tests to install a custom MeterProvider."""
    global _CONFIGURED, _meter, _http_requests, _plan_requests, _wiki_requests, _integration_calls
    _CONFIGURED = False
    _meter = None
    _http_requests = None
    _plan_requests = None
    _wiki_requests = None
    _integration_calls = None
    from opentelemetry.metrics import _internal as metrics_internal

    metrics_internal._METER_PROVIDER_SET_ONCE._done = False  # noqa: SLF001
    metrics_internal._METER_PROVIDER = None  # noqa: SLF001


def configure_metrics() -> None:
    global _CONFIGURED, _meter
    if _CONFIGURED:
        return
    readers: list[PeriodicExportingMetricReader] = []
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    if endpoint:
        exporter = OTLPMetricExporter(endpoint=endpoint)
        readers.append(PeriodicExportingMetricReader(exporter))
    provider = MeterProvider(resource=_service_resource(), metric_readers=readers)
    metrics.set_meter_provider(provider)
    _meter = metrics.get_meter("climbit.telemetry")
    _CONFIGURED = True


def _get_meter() -> metrics.Meter:
    configure_metrics()
    assert _meter is not None
    return _meter


def http_route_template(path: str) -> str:
    if path == "/routes/gpx-upload":
        return "/routes/gpx-upload"
    if _ROUTE_ID.match(path):
        if path.endswith("/plans"):
            return "/routes/{route_id}/plans"
        if path.endswith("/descriptive"):
            return "/routes/{route_id}/descriptive"
        if path.endswith("/protected-edits"):
            return "/routes/{route_id}/protected-edits"
        return "/routes/{route_id}"
    return path


def status_class(status_code: int) -> str:
    return f"{status_code // 100}xx"


def _http_requests_counter() -> Counter:
    global _http_requests
    if _http_requests is None:
        _http_requests = _get_meter().create_counter(
            "climbit.http.server.requests",
            description="HTTP requests by route template and status class",
        )
    return _http_requests


def _plan_requests_counter() -> Counter:
    global _plan_requests
    if _plan_requests is None:
        _plan_requests = _get_meter().create_counter(
            "climbit.plan.requests",
            description="Trip plan POST outcomes",
        )
    return _plan_requests


def _wiki_requests_counter() -> Counter:
    global _wiki_requests
    if _wiki_requests is None:
        _wiki_requests = _get_meter().create_counter(
            "climbit.wiki.requests",
            description="Anonymous wiki edit activity",
        )
    return _wiki_requests


def _integration_calls_counter() -> Counter:
    global _integration_calls
    if _integration_calls is None:
        _integration_calls = _get_meter().create_counter(
            "climbit.integration.calls",
            description="Planning integration outcomes",
        )
    return _integration_calls


def record_http_request(*, route: str, method: str, status_code: int) -> None:
    _http_requests_counter().add(
        1,
        {
            "route": route,
            "method": method.upper(),
            "status_class": status_class(status_code),
        },
    )


def record_plan_request(*, status_code: int) -> None:
    result = "success" if status_code == 200 else "failure"
    _plan_requests_counter().add(1, {"result": result})


def record_wiki_request(*, operation: str, status_code: int) -> None:
    _wiki_requests_counter().add(
        1,
        {
            "operation": operation,
            "status_class": status_class(status_code),
        },
    )


def wiki_operation_for_request(method: str, path: str) -> str | None:
    template = http_route_template(path)
    if template == "/routes/gpx-upload" and method.upper() == "POST":
        return "gpx_upload"
    if template == "/routes/{route_id}/descriptive" and method.upper() == "PATCH":
        return "descriptive_edit"
    if template == "/routes/{route_id}/protected-edits" and method.upper() == "POST":
        return "protected_edit"
    return None


def record_integration_call(*, integration: str, outcome: str) -> None:
    _integration_calls_counter().add(
        1,
        {
            "integration": integration,
            "outcome": outcome,
        },
    )


def component_status_to_outcome(status: str) -> str:
    if status == "ok":
        return "ok"
    if status == "degraded":
        return "degraded"
    return "unknown"
