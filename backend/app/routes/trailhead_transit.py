from __future__ import annotations

import math
from dataclasses import dataclass

from app.domain.route import Point
from app.domain.route import Route
from app.planning.transit import TRANSIT_HUBS
from app.planning.transit import TransitHub
from app.planning.versions import TRAILHEAD_TRANSIT_MAX_DISTANCE_M


@dataclass(frozen=True, slots=True)
class TrailheadTransitConnection:
    hub_id: str
    stop_name: str
    latitude: float
    longitude: float
    distance_m: float


def _haversine_m(a_lat: float, a_lon: float, b_lat: float, b_lon: float) -> float:
    radius = 6_371_000.0
    lat1, lon1 = math.radians(a_lat), math.radians(a_lon)
    lat2, lon2 = math.radians(b_lat), math.radians(b_lon)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    return 2 * radius * math.asin(min(1.0, math.sqrt(h)))


def _connection_from_hub(
    hub: TransitHub, trailhead: Point
) -> TrailheadTransitConnection:
    distance = _haversine_m(
        trailhead.latitude, trailhead.longitude, hub.latitude, hub.longitude
    )
    return TrailheadTransitConnection(
        hub_id=hub.hub_id,
        stop_name=hub.name,
        latitude=hub.latitude,
        longitude=hub.longitude,
        distance_m=round(distance, 1),
    )


def resolve_trailhead_transit_connection(
    route: Route,
) -> TrailheadTransitConnection | None:
    if route.trailhead is None:
        return None
    trailhead = route.trailhead
    best: TrailheadTransitConnection | None = None
    for hub in TRANSIT_HUBS:
        candidate = _connection_from_hub(hub, trailhead)
        if candidate.distance_m > TRAILHEAD_TRANSIT_MAX_DISTANCE_M:
            continue
        if best is None or candidate.distance_m < best.distance_m:
            best = candidate
    return best
