from __future__ import annotations

import json
from datetime import date
from datetime import datetime
from datetime import timezone
from pathlib import Path

import httpx
import pytest

from app.data.seed_routes import PUBLISHED_ALPINE_HIKE_SLUG
from app.data.seed_routes import build_seed_routes
from app.data.seed_routes import seed_route_id
from app.planning.transit import ComponentStatus
from app.planning.transit import MockTransitAdapter
from app.planning.transit import TransitSummary
from app.planning.transit import TransitousAdapter
from app.planning.transit import apply_last_return_recommendation
from app.planning.transit import resolve_transit_hub
from app.planning.versions import MOCK_TRANSIT_ADAPTER_VERSION
from app.planning.versions import TRANSITOUS_ADAPTER_VERSION

FIXTURES = Path(__file__).resolve().parent / "data" / "transitous"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _chamonix_route():
    return next(
        route
        for route_id, route in build_seed_routes()
        if route_id == seed_route_id(PUBLISHED_ALPINE_HIKE_SLUG)
    )


def _frozen_query_time() -> datetime:
    return datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)


def test_mock_adapter_unknown_origin_is_degraded() -> None:
    adapter = MockTransitAdapter()
    summary = adapter.plan_transit(
        origin="unknown",
        route=_chamonix_route(),
        plan_date=date(2026, 7, 15),
        start_time_local=None,
        query_time=_frozen_query_time(),
    )
    assert summary.status is ComponentStatus.DEGRADED
    assert summary.last_return_feasible is None
    assert summary.adapter_version == MOCK_TRANSIT_ADAPTER_VERSION


def test_unresolved_hub_yields_degraded_transitous() -> None:
    adapter = TransitousAdapter(client=httpx.Client())
    summary = adapter.plan_transit(
        origin="somewhere with no hub alias",
        route=_chamonix_route(),
        plan_date=date(2026, 7, 15),
        start_time_local=None,
        query_time=_frozen_query_time(),
    )
    adapter.close()
    assert summary.status is ComponentStatus.DEGRADED
    assert summary.last_return_feasible is None
    assert "could not be resolved" in summary.summary.lower()


def test_empty_itineraries_degraded() -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            200, json=_load_fixture("empty_itineraries.json")
        )
    )
    client = httpx.Client(transport=transport)
    adapter = TransitousAdapter(client=client)
    summary = adapter.plan_transit(
        origin="Chamonix village",
        route=_chamonix_route(),
        plan_date=date(2026, 7, 15),
        start_time_local=None,
        query_time=_frozen_query_time(),
    )
    assert summary.status is ComponentStatus.DEGRADED
    assert summary.last_return_feasible is None
    assert "no public-transport itinerary" in summary.summary.lower()


def test_multi_day_outbound_degraded() -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            200, json=_load_fixture("multi_day_outbound.json")
        )
    )
    client = httpx.Client(transport=transport)
    adapter = TransitousAdapter(client=client)
    summary = adapter.plan_transit(
        origin="geneva",
        route=_chamonix_route(),
        plan_date=date(2026, 7, 15),
        start_time_local=None,
        query_time=_frozen_query_time(),
    )
    assert summary.status is ComponentStatus.DEGRADED
    assert "same-day outbound" in summary.summary.lower()


def test_timeout_yields_unknown() -> None:
    def _timeout(_request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=_request)

    client = httpx.Client(transport=httpx.MockTransport(_timeout))
    adapter = TransitousAdapter(client=client, timeout_seconds=0.001)
    summary = adapter.plan_transit(
        origin="munich",
        route=_chamonix_route(),
        plan_date=date(2026, 7, 15),
        start_time_local=None,
        query_time=_frozen_query_time(),
    )
    assert summary.status is ComponentStatus.UNKNOWN


def test_same_day_outbound_ok_with_return_feasible() -> None:
    responses = [
        _load_fixture("same_day_outbound.json"),
        _load_fixture("return_after_buffer.json"),
    ]
    call_index = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        payload = responses[min(call_index["n"], len(responses) - 1)]
        call_index["n"] += 1
        return httpx.Response(200, json=payload)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = TransitousAdapter(client=client)
    summary = adapter.plan_transit(
        origin="Munich Hauptbahnhof",
        route=_chamonix_route(),
        plan_date=date(2026, 7, 15),
        start_time_local=None,
        query_time=_frozen_query_time(),
    )
    assert summary.status is ComponentStatus.OK
    assert summary.adapter_version == TRANSITOUS_ADAPTER_VERSION
    assert summary.last_return_feasible is True
    assert "walking" in summary.summary.lower()
    assert "best-effort" in summary.summary.lower()


def test_last_return_missed_when_return_empty() -> None:
    responses = [
        _load_fixture("same_day_outbound.json"),
        _load_fixture("empty_itineraries.json"),
    ]
    call_index = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        payload = responses[min(call_index["n"], len(responses) - 1)]
        call_index["n"] += 1
        return httpx.Response(200, json=payload)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = TransitousAdapter(client=client)
    summary = adapter.plan_transit(
        origin="munich",
        route=_chamonix_route(),
        plan_date=date(2026, 7, 15),
        start_time_local=None,
        query_time=_frozen_query_time(),
    )
    assert summary.status is ComponentStatus.OK
    assert summary.last_return_feasible is False


def test_apply_last_return_forces_red_recommendation() -> None:
    transit = TransitSummary(
        status=ComponentStatus.OK,
        adapter_version=TRANSITOUS_ADAPTER_VERSION,
        summary="ok",
        origin_region="DE-BY",
        last_return_feasible=False,
        source_time=_frozen_query_time(),
    )
    rec, _conf, explanation = apply_last_return_recommendation(
        recommendation="green",
        confidence="high",
        explanation=["Critical inputs present and fresh."],
        transit=transit,
    )
    assert rec == "red"
    assert any("return connection" in line.lower() for line in explanation)


def test_resolve_hub_aliases() -> None:
    assert resolve_transit_hub("Munich platform 11") is not None
    assert resolve_transit_hub("n/a") is None
