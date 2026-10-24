from __future__ import annotations

import math
from dataclasses import dataclass

from app.domain.route import Point
from app.domain.route import Route


@dataclass(frozen=True, slots=True)
class ElevationProfilePoint:
    distance_m: float
    elevation_m: int


@dataclass(frozen=True, slots=True)
class ElevationProfile:
    points: tuple[ElevationProfilePoint, ...]
    synthesized: bool


def _haversine_m(a: Point, b: Point) -> float:
    radius = 6_371_000.0
    lat1, lon1 = math.radians(a.latitude), math.radians(a.longitude)
    lat2, lon2 = math.radians(b.latitude), math.radians(b.longitude)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * radius * math.asin(min(1.0, math.sqrt(h)))


def build_elevation_profile(route: Route) -> ElevationProfile | None:
    if route.linestring is None or len(route.linestring.points) < 2:
        return None
    if route.elevation_min_m is None or route.elevation_max_m is None:
        return None

    points = route.linestring.points
    cumulative = [0.0]
    for index in range(1, len(points)):
        cumulative.append(cumulative[-1] + _haversine_m(points[index - 1], points[index]))
    total = cumulative[-1]
    if total <= 0:
        return None

    min_e = float(route.elevation_min_m)
    max_e = float(route.elevation_max_m)
    profile: list[ElevationProfilePoint] = []
    for distance, _point in zip(cumulative, points, strict=True):
        fraction = distance / total
        if len(points) == 2:
            elevation = min_e + (max_e - min_e) * fraction
        else:
            elevation = min_e + (max_e - min_e) * math.sin(math.pi * fraction)
        profile.append(
            ElevationProfilePoint(distance_m=round(distance, 1), elevation_m=int(round(elevation)))
        )
    return ElevationProfile(points=tuple(profile), synthesized=True)
