from __future__ import annotations

import json
import os
from dataclasses import dataclass
from dataclasses import replace
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from datetime import timezone
from enum import StrEnum
from typing import Any
from typing import Protocol
from urllib.parse import urlencode
from uuid import UUID
from zoneinfo import ZoneInfo

import httpx

from app.domain.route import Route
from app.planning.daylight import trailhead_timezone
from app.planning.versions import MOCK_TRANSIT_ADAPTER_VERSION
from app.planning.versions import SAFETY_BUFFER_MINUTES
from app.planning.versions import TRANSIT_FALLBACK_CACHE_MAX_AGE_SECONDS
from app.planning.versions import TRANSIT_TIMETABLE_MAX_AGE_SECONDS
from app.planning.versions import TRANSITOUS_ADAPTER_VERSION

DEFAULT_OUTBOUND_DEPARTURE_LOCAL = time(7, 0)
TRANSIT_HTTP_TIMEOUT_SECONDS = 5
DEFAULT_TRANSITOUS_PLAN_URL = "https://api.transitous.org/api/v1/plan"
DEFAULT_TRANSIT_USER_AGENT = (
    "ClimbIt/1.0 (https://github.com/Franky007Bond/ClimbIt; alpine trip planning)"
)

BEST_EFFORT_DISCLAIMER = "Timetables are best-effort and not guaranteed."


class ComponentStatus(StrEnum):
    OK = "ok"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class TransitSummary:
    status: ComponentStatus
    adapter_version: str
    summary: str
    origin_region: str | None
    last_return_feasible: bool | None
    source_time: datetime
    live_available: bool = False
    journey_planner_url: str | None = None


@dataclass(frozen=True, slots=True)
class _TransitFallbackCacheEntry:
    summary: str
    source_time: datetime


# In-process per worker; lost on restart (issue #44).
_TRANSIT_FALLBACK_CACHE: dict[tuple[str, str, str, str], _TransitFallbackCacheEntry] = {}


@dataclass(frozen=True, slots=True)
class TransitHub:
    hub_id: str
    name: str
    latitude: float
    longitude: float
    origin_region: str
    aliases: tuple[str, ...]


# Versioned hub catalog (issue #43 / spike #42). Origins match via case-insensitive substring.
TRANSIT_HUBS: tuple[TransitHub, ...] = (
    TransitHub(
        hub_id="de-muenchen-hbf",
        name="München Hauptbahnhof",
        latitude=48.140,
        longitude=11.558,
        origin_region="DE-BY",
        aliases=("munich", "münchen", "muenchen"),
    ),
    TransitHub(
        hub_id="ch-geneve",
        name="Genève Cornavin",
        latitude=46.210,
        longitude=6.142,
        origin_region="CH-GE",
        aliases=("geneva", "genève", "geneve"),
    ),
    TransitHub(
        hub_id="fr-chamonix",
        name="Chamonix-Mont-Blanc",
        latitude=45.872,
        longitude=6.984,
        origin_region="FR-74",
        aliases=("chamonix",),
    ),
    TransitHub(
        hub_id="at-innsbruck-hbf",
        name="Innsbruck Hauptbahnhof",
        latitude=47.263,
        longitude=11.401,
        origin_region="AT-T",
        aliases=("innsbruck",),
    ),
    TransitHub(
        hub_id="it-bolzano",
        name="Bolzano",
        latitude=46.498,
        longitude=11.358,
        origin_region="IT-32",
        aliases=("bolzano", "bozen"),
    ),
    TransitHub(
        hub_id="ch-zuerich-hbf",
        name="Zürich Hauptbahnhof",
        latitude=47.378,
        longitude=8.540,
        origin_region="CH-ZH",
        aliases=("zürich", "zurich", "zuerich"),
    ),
)


class TransitPort(Protocol):
    adapter_version: str

    def plan_transit(
        self,
        *,
        origin: str,
        route: Route,
        plan_date: date,
        start_time_local: time | None,
        query_time: datetime,
    ) -> TransitSummary: ...


def get_transit_port() -> TransitPort:
    adapter = os.environ.get("TRANSIT_ADAPTER", "mock").strip().lower()
    if adapter == "transitous":
        return TransitousAdapter()
    return MockTransitAdapter()


def resolve_transit_hub(origin: str) -> TransitHub | None:
    cleaned = origin.strip().lower()
    if not cleaned or cleaned in {"unknown", "n/a"}:
        return None
    for hub in TRANSIT_HUBS:
        if any(alias in cleaned for alias in hub.aliases):
            return hub
    return None


def _coarse_origin_region(origin: str) -> str | None:
    hub = resolve_transit_hub(origin)
    if hub is not None:
        return hub.origin_region
    cleaned = origin.strip()
    if not cleaned:
        return None
    if cleaned.lower() in {"unknown", "n/a"}:
        return None
    return "region-unknown"


def _default_departure_local(start_time_local: time | None) -> time:
    return (
        start_time_local
        if start_time_local is not None
        else DEFAULT_OUTBOUND_DEPARTURE_LOCAL
    )


def _local_departure_datetime(
    plan_date: date, departure_local: time, tz_name: str
) -> datetime:
    tz = ZoneInfo(tz_name)
    return datetime.combine(plan_date, departure_local, tzinfo=tz)


def _format_plan_time(when: datetime) -> str:
    return when.isoformat(timespec="seconds")


def _transit_assumption_suffix(
    departure_local: time, tz_name: str, *, start_time_local: time | None
) -> str:
    if start_time_local is not None:
        return (
            f" Outbound departure {departure_local.strftime('%H:%M')} {tz_name}. "
            f"{BEST_EFFORT_DISCLAIMER}"
        )
    return (
        f" Outbound departure {departure_local.strftime('%H:%M')} {tz_name} "
        f"(default 07:00 when start time omitted). {BEST_EFFORT_DISCLAIMER}"
    )


def _fallback_cache_key(
    *,
    hub_id: str,
    route_id: UUID,
    plan_date: date,
    departure_local: time,
) -> tuple[str, str, str, str]:
    return (
        hub_id,
        str(route_id),
        plan_date.isoformat(),
        departure_local.isoformat(),
    )


def _is_unresolved_origin_summary(summary: str) -> bool:
    lowered = summary.lower()
    return "origin could not be resolved" in lowered


def _is_no_itinerary_degraded(summary: TransitSummary) -> bool:
    return (
        summary.status is ComponentStatus.DEGRADED
        and "no public-transport itinerary" in summary.summary.lower()
    )


def build_journey_planner_url(
    *,
    from_lat: float,
    from_lon: float,
    to_lat: float,
    to_lon: float,
    departure: datetime,
    plan_url: str | None = None,
) -> str:
    base = (
        plan_url
        or os.environ.get("TRANSITOUS_PLAN_URL", DEFAULT_TRANSITOUS_PLAN_URL).strip()
    )
    params = {
        "fromPlace": f"{from_lat},{from_lon}",
        "toPlace": f"{to_lat},{to_lon}",
        "time": _format_plan_time(departure),
        "arriveBy": "false",
        "numItineraries": "3",
    }
    return f"{base}?{urlencode(params)}"


def _transit_source_age_seconds(source_time: datetime, query_time: datetime) -> float:
    return (query_time - source_time).total_seconds()


def _lookup_fresh_fallback_cache(
    cache_key: tuple[str, str, str, str], query_time: datetime
) -> _TransitFallbackCacheEntry | None:
    entry = _TRANSIT_FALLBACK_CACHE.get(cache_key)
    if entry is None:
        return None
    age = _transit_source_age_seconds(entry.source_time, query_time)
    if age > TRANSIT_FALLBACK_CACHE_MAX_AGE_SECONDS:
        return None
    return entry


class CachedTransitBoundary:
    """Cache boundary for transit; stores last successful live outbound per plan key."""

    def __init__(self, inner: TransitPort, *, route_id: UUID) -> None:
        self._inner = inner
        self._route_id = route_id

    @property
    def adapter_version(self) -> str:
        return self._inner.adapter_version

    def plan_transit(
        self,
        *,
        origin: str,
        route: Route,
        plan_date: date,
        start_time_local: time | None,
        query_time: datetime,
    ) -> TransitSummary:
        hub = resolve_transit_hub(origin)
        departure_local = _default_departure_local(start_time_local)
        tz_name = trailhead_timezone(route)
        assumption = _transit_assumption_suffix(
            departure_local, tz_name, start_time_local=start_time_local
        )
        cache_key: tuple[str, str, str, str] | None = None
        if hub is not None:
            cache_key = _fallback_cache_key(
                hub_id=hub.hub_id,
                route_id=self._route_id,
                plan_date=plan_date,
                departure_local=departure_local,
            )

        inner = self._inner.plan_transit(
            origin=origin,
            route=route,
            plan_date=plan_date,
            start_time_local=start_time_local,
            query_time=query_time,
        )

        if _is_unresolved_origin_summary(inner.summary):
            return replace(
                inner,
                live_available=False,
                journey_planner_url=None,
            )

        if inner.status is ComponentStatus.OK:
            age = _transit_source_age_seconds(inner.source_time, query_time)
            if age <= TRANSIT_TIMETABLE_MAX_AGE_SECONDS:
                if cache_key is not None:
                    _TRANSIT_FALLBACK_CACHE[cache_key] = _TransitFallbackCacheEntry(
                        summary=inner.summary,
                        source_time=inner.source_time,
                    )
                return replace(
                    inner,
                    live_available=True,
                    journey_planner_url=None,
                )
            return self._apply_live_unavailable_fallback(
                inner=inner,
                hub=hub,
                route=route,
                plan_date=plan_date,
                departure_local=departure_local,
                assumption=assumption,
                cache_key=cache_key,
                query_time=query_time,
                reason_prefix="Live timetable data was stale.",
            )

        if inner.status is ComponentStatus.UNKNOWN or _is_no_itinerary_degraded(inner):
            return self._apply_live_unavailable_fallback(
                inner=inner,
                hub=hub,
                route=route,
                plan_date=plan_date,
                departure_local=departure_local,
                assumption=assumption,
                cache_key=cache_key,
                query_time=query_time,
                reason_prefix="Live public transport timetables were unavailable.",
            )

        return replace(
            inner,
            live_available=False,
            journey_planner_url=None,
        )

    def _apply_live_unavailable_fallback(
        self,
        *,
        inner: TransitSummary,
        hub: TransitHub | None,
        route: Route,
        plan_date: date,
        departure_local: time,
        assumption: str,
        cache_key: tuple[str, str, str, str] | None,
        query_time: datetime,
        reason_prefix: str,
    ) -> TransitSummary:
        cached = (
            _lookup_fresh_fallback_cache(cache_key, query_time)
            if cache_key is not None
            else None
        )
        if cached is not None:
            summary = (
                f"{reason_prefix} {cached.summary}"
                if reason_prefix.endswith(".")
                else f"{reason_prefix}. {cached.summary}"
            )
            return replace(
                inner,
                status=ComponentStatus.DEGRADED,
                summary=summary,
                last_return_feasible=None,
                source_time=query_time,
                live_available=False,
                journey_planner_url=None,
            )

        if hub is not None and route.trailhead is not None:
            outbound_departure = _local_departure_datetime(
                plan_date, departure_local, trailhead_timezone(route)
            )
            planner_url = build_journey_planner_url(
                from_lat=hub.latitude,
                from_lon=hub.longitude,
                to_lat=route.trailhead.latitude,
                to_lon=route.trailhead.longitude,
                departure=outbound_departure,
            )
            summary = (
                f"{reason_prefix} Use this journey planner link for outbound options: "
                f"{planner_url}.{assumption}"
            )
            return replace(
                inner,
                status=ComponentStatus.DEGRADED,
                summary=summary,
                last_return_feasible=None,
                source_time=query_time,
                live_available=False,
                journey_planner_url=planner_url,
            )

        return replace(
            inner,
            live_available=False,
            journey_planner_url=None,
            last_return_feasible=None,
        )


class MockTransitAdapter:
    adapter_version = MOCK_TRANSIT_ADAPTER_VERSION

    def plan_transit(
        self,
        *,
        origin: str,
        route: Route,
        plan_date: date,
        start_time_local: time | None,
        query_time: datetime,
    ) -> TransitSummary:
        del route, plan_date
        region = _coarse_origin_region(origin)
        degraded = origin.strip().lower() in {"", "unknown", "n/a"}
        status = ComponentStatus.DEGRADED if degraded else ComponentStatus.OK
        departure = _default_departure_local(start_time_local)
        assumption = (
            f" Assumes outbound departure at {departure.strftime('%H:%M')} local when "
            "start time is omitted."
        )
        return TransitSummary(
            status=status,
            adapter_version=self.adapter_version,
            summary="Mock outbound connection to trailhead access point." + assumption,
            origin_region=region,
            last_return_feasible=True if not degraded else None,
            source_time=query_time,
        )


class TransitousAdapter:
    """Transitous/MOTIS public /plan client (see _docs/integrations.md)."""

    adapter_version = TRANSITOUS_ADAPTER_VERSION

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        plan_url: str | None = None,
        user_agent: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self._plan_url = (
            plan_url
            or os.environ.get(
                "TRANSITOUS_PLAN_URL", DEFAULT_TRANSITOUS_PLAN_URL
            ).strip()
        )
        self._user_agent = (
            user_agent
            or os.environ.get("TRANSIT_USER_AGENT", DEFAULT_TRANSIT_USER_AGENT).strip()
        )
        timeout = timeout_seconds
        if timeout is None:
            raw = os.environ.get(
                "TRANSIT_HTTP_TIMEOUT_SECONDS", str(TRANSIT_HTTP_TIMEOUT_SECONDS)
            )
            timeout = float(raw.strip())
        self._timeout = timeout
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=self._timeout)

    def plan_transit(
        self,
        *,
        origin: str,
        route: Route,
        plan_date: date,
        start_time_local: time | None,
        query_time: datetime,
    ) -> TransitSummary:
        hub = resolve_transit_hub(origin)
        region = hub.origin_region if hub is not None else _coarse_origin_region(origin)
        if hub is None:
            return TransitSummary(
                status=ComponentStatus.DEGRADED,
                adapter_version=self.adapter_version,
                summary=(
                    "Public transport could not be planned because the origin could not be "
                    "resolved to a configured travel hub."
                ),
                origin_region=region,
                last_return_feasible=None,
                source_time=query_time,
            )
        if route.trailhead is None or route.duration_minutes is None:
            return TransitSummary(
                status=ComponentStatus.UNKNOWN,
                adapter_version=self.adapter_version,
                summary="Route trailhead or duration is missing; transit could not be evaluated.",
                origin_region=region,
                last_return_feasible=None,
                source_time=query_time,
            )

        tz_name = trailhead_timezone(route)
        departure_local = _default_departure_local(start_time_local)
        outbound_departure = _local_departure_datetime(
            plan_date, departure_local, tz_name
        )
        assumption = (
            f" Outbound departure {departure_local.strftime('%H:%M')} {tz_name} "
            f"(default 07:00 when start time omitted). {BEST_EFFORT_DISCLAIMER}"
        )

        outbound_payload = self._fetch_plan(
            from_lat=hub.latitude,
            from_lon=hub.longitude,
            to_lat=route.trailhead.latitude,
            to_lon=route.trailhead.longitude,
            departure=outbound_departure,
        )
        if outbound_payload is None:
            return TransitSummary(
                status=ComponentStatus.UNKNOWN,
                adapter_version=self.adapter_version,
                summary=(
                    "Public transport lookup failed or timed out; status is unknown."
                    + assumption
                ),
                origin_region=region,
                last_return_feasible=None,
                source_time=query_time,
            )

        itineraries = outbound_payload.get("itineraries") or []
        if not itineraries:
            return TransitSummary(
                status=ComponentStatus.DEGRADED,
                adapter_version=self.adapter_version,
                summary=(
                    "No public-transport itinerary was found for this origin and trailhead."
                    + assumption
                ),
                origin_region=region,
                last_return_feasible=None,
                source_time=query_time,
            )

        best = itineraries[0]
        tz = ZoneInfo(tz_name)
        if not _itinerary_same_calendar_day(best, plan_date, tz):
            return TransitSummary(
                status=ComponentStatus.DEGRADED,
                adapter_version=self.adapter_version,
                summary=(
                    "Same-day outbound public transport could not be confirmed; the best "
                    "itinerary spans more than one calendar day." + assumption
                ),
                origin_region=region,
                last_return_feasible=None,
                source_time=query_time,
            )

        summary = _format_ok_summary(best, assumption)
        hike_finish = outbound_departure + timedelta(minutes=route.duration_minutes)
        return_departure = hike_finish + timedelta(minutes=SAFETY_BUFFER_MINUTES)
        return_payload = self._fetch_plan(
            from_lat=route.trailhead.latitude,
            from_lon=route.trailhead.longitude,
            to_lat=hub.latitude,
            to_lon=hub.longitude,
            departure=return_departure,
        )
        last_return = _evaluate_last_return(return_payload, return_departure, tz)

        return TransitSummary(
            status=ComponentStatus.OK,
            adapter_version=self.adapter_version,
            summary=summary,
            origin_region=region,
            last_return_feasible=last_return,
            source_time=query_time,
        )

    def _fetch_plan(
        self,
        *,
        from_lat: float,
        from_lon: float,
        to_lat: float,
        to_lon: float,
        departure: datetime,
    ) -> dict[str, Any] | None:
        params = {
            "fromPlace": f"{from_lat},{from_lon}",
            "toPlace": f"{to_lat},{to_lon}",
            "time": _format_plan_time(departure),
            "arriveBy": "false",
            "numItineraries": "3",
        }
        url = f"{self._plan_url}?{urlencode(params)}"
        headers = {"User-Agent": self._user_agent, "Accept": "application/json"}
        try:
            response = self._client.get(url, headers=headers, timeout=self._timeout)
            response.raise_for_status()
        except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError):
            return None
        try:
            payload = response.json()
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None
        return payload

    def close(self) -> None:
        if self._owns_client:
            self._client.close()


def _itinerary_epoch_ms(itinerary: dict[str, Any], key: str) -> int | None:
    value = itinerary.get(key)
    if isinstance(value, (int, float)):
        return int(value)
    return None


def _itinerary_same_calendar_day(
    itinerary: dict[str, Any], plan_date: date, tz: ZoneInfo
) -> bool:
    start_ms = _itinerary_epoch_ms(itinerary, "startTime")
    end_ms = _itinerary_epoch_ms(itinerary, "endTime")
    if start_ms is None or end_ms is None:
        return False
    start_local = datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc).astimezone(
        tz
    )
    end_local = datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc).astimezone(tz)
    return start_local.date() == plan_date and end_local.date() == plan_date


def _leg_mode(leg: dict[str, Any]) -> str:
    mode = leg.get("mode")
    return str(mode).upper() if mode is not None else ""


def _itinerary_walk_minutes(itinerary: dict[str, Any]) -> int:
    legs = itinerary.get("legs") or []
    walk_seconds = 0
    for leg in legs:
        if not isinstance(leg, dict):
            continue
        if _leg_mode(leg) == "WALK":
            duration = leg.get("duration")
            if isinstance(duration, (int, float)):
                walk_seconds += int(duration)
    return max(walk_seconds // 60, 0)


def _itinerary_transfer_count(itinerary: dict[str, Any]) -> int:
    legs = itinerary.get("legs") or []
    transit_legs = sum(
        1
        for leg in legs
        if isinstance(leg, dict) and _leg_mode(leg) not in {"", "WALK"}
    )
    return max(transit_legs - 1, 0)


def _itinerary_duration_minutes(itinerary: dict[str, Any]) -> int:
    duration = itinerary.get("duration")
    if isinstance(duration, (int, float)):
        return max(int(duration) // 60, 0)
    start_ms = _itinerary_epoch_ms(itinerary, "startTime")
    end_ms = _itinerary_epoch_ms(itinerary, "endTime")
    if start_ms is not None and end_ms is not None:
        return max((end_ms - start_ms) // 60000, 0)
    return 0


def _format_ok_summary(itinerary: dict[str, Any], assumption_suffix: str) -> str:
    walk_min = _itinerary_walk_minutes(itinerary)
    transfers = _itinerary_transfer_count(itinerary)
    duration_min = _itinerary_duration_minutes(itinerary)
    transfer_word = "transfer" if transfers == 1 else "transfers"
    return (
        f"Outbound public transport about {duration_min} min including {walk_min} min walking "
        f"and {transfers} {transfer_word}."
        f"{assumption_suffix}"
    )


def _evaluate_last_return(
    return_payload: dict[str, Any] | None,
    return_departure: datetime,
    tz: ZoneInfo,
) -> bool | None:
    if return_payload is None:
        return None
    itineraries = return_payload.get("itineraries") or []
    if not itineraries:
        return False
    departure_ms = int(return_departure.timestamp() * 1000)
    for itinerary in itineraries:
        if not isinstance(itinerary, dict):
            continue
        start_ms = _itinerary_epoch_ms(itinerary, "startTime")
        end_ms = _itinerary_epoch_ms(itinerary, "endTime")
        if start_ms is None or end_ms is None:
            continue
        if start_ms >= departure_ms:
            end_local = datetime.fromtimestamp(
                end_ms / 1000, tz=timezone.utc
            ).astimezone(tz)
            if end_local >= return_departure:
                return True
    return False


def apply_transit_recommendation(
    *,
    recommendation: str,
    confidence: str,
    explanation: list[str],
    transit: TransitSummary,
) -> tuple[str, str, list[str]]:
    if transit.status is ComponentStatus.UNKNOWN and recommendation in {
        "green",
        "yellow",
    }:
        return "unknown", confidence, explanation
    if transit.status is ComponentStatus.DEGRADED and recommendation == "green":
        return "yellow", confidence, explanation
    return recommendation, confidence, explanation


def apply_last_return_recommendation(
    *,
    recommendation: str,
    confidence: str,
    explanation: list[str],
    transit: TransitSummary,
) -> tuple[str, str, list[str]]:
    if transit.status is ComponentStatus.OK and transit.last_return_feasible is False:
        explanation = list(explanation)
        explanation.append(
            "The last feasible return connection would be missed after the planned hike."
        )
        return "red", confidence, explanation
    return recommendation, confidence, explanation
