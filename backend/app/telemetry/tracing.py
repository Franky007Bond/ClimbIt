from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Literal

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

PlanningStep = Literal[
    "weather",
    "avalanche",
    "transit",
    "gear",
    "recommendation",
    "database",
]

_TRACER_NAME = "climbit.planning"
_CONFIGURED = False


def configure_tracing() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    service_name = os.environ.get("OTEL_SERVICE_NAME", "climbit-api").strip() or "climbit-api"
    service_version = os.environ.get("OTEL_SERVICE_VERSION", "dev").strip() or "dev"
    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": service_version,
        }
    )
    provider = TracerProvider(resource=resource)
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    if endpoint:
        exporter = OTLPSpanExporter(endpoint=endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _CONFIGURED = True


def reset_tracing_for_tests() -> None:
    """Allow tests to install a custom TracerProvider."""
    global _CONFIGURED
    _CONFIGURED = False


def install_tracer_provider(provider: TracerProvider) -> None:
    global _CONFIGURED
    trace.set_tracer_provider(provider)
    _CONFIGURED = True


def get_planning_tracer() -> trace.Tracer:
    configure_tracing()
    return trace.get_tracer(_TRACER_NAME)


def current_trace_id() -> str | None:
    span = trace.get_current_span()
    context = span.get_span_context()
    if not context.is_valid:
        return None
    return trace.format_trace_id(context.trace_id)


@contextmanager
def plan_build_trace() -> Iterator[None]:
    tracer = get_planning_tracer()
    with tracer.start_as_current_span("plan.build"):
        yield


@contextmanager
def planning_step(step: PlanningStep) -> Iterator[None]:
    tracer = get_planning_tracer()
    with tracer.start_as_current_span(
        f"planning.{step}",
        attributes={"planning.step": step},
    ):
        yield
