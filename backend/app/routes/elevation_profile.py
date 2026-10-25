from __future__ import annotations

import math
from dataclasses import dataclass

from app.domain.route import Point
from app.domain.route import Route
from app.gpx.process import GpxValidationError
from app.gpx.process import parse_gpx_track_points

ELEVATION_PROFILE_MAX_POINTS = 500


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
    h = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    return 2 * radius * math.asin(min(1.0, math.sqrt(h)))


def _haversine_coords_m(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    return _haversine_m(
        Point(longitude=lon1, latitude=lat1),
        Point(longitude=lon2, latitude=lat2),
    )


def _cumulative_distances_for_points(points: list[Point]) -> list[float] | None:
    cumulative = [0.0]
    for index in range(1, len(points)):
        cumulative.append(
            cumulative[-1] + _haversine_m(points[index - 1], points[index])
        )
    if cumulative[-1] <= 0:
        return None
    return cumulative


def _cumulative_distances_for_track(
    track: list[tuple[float, float, float]],
) -> list[float] | None:
    cumulative = [0.0]
    for index in range(1, len(track)):
        lon1, lat1, _ = track[index - 1]
        lon2, lat2, _ = track[index]
        cumulative.append(
            cumulative[-1]
            + _haversine_coords_m(lat1, lon1, lat2, lon2)
        )
    if cumulative[-1] <= 0:
        return None
    return cumulative


def _interpolate_elevation_at_distance(
    track: list[tuple[float, float, float]],
    track_distances: list[float],
    distance_m: float,
) -> int:
    if distance_m <= track_distances[0]:
        return int(round(track[0][2]))
    if distance_m >= track_distances[-1]:
        return int(round(track[-1][2]))
    for index in range(1, len(track_distances)):
        upper = track_distances[index]
        if distance_m > upper:
            continue
        lower = track_distances[index - 1]
        span = upper - lower
        if span <= 0:
            return int(round(track[index][2]))
        fraction = (distance_m - lower) / span
        lower_ele = track[index - 1][2]
        upper_ele = track[index][2]
        return int(round(lower_ele + (upper_ele - lower_ele) * fraction))
    return int(round(track[-1][2]))


def _elevations_from_gpx_for_linestring(
    gpx_track: list[tuple[float, float, float | None]],
    linestring_points: list[Point],
    line_distances: list[float],
) -> list[int] | None:
    if any(elevation is None for _, _, elevation in gpx_track):
        return None
    track: list[tuple[float, float, float]] = [
        (lon, lat, float(elevation))
        for lon, lat, elevation in gpx_track
        if elevation is not None
    ]
    if len(track) < 2:
        return None

    if len(track) == len(linestring_points):
        return [int(round(point[2])) for point in track]

    track_distances = _cumulative_distances_for_track(track)
    if track_distances is None:
        return None
    return [
        _interpolate_elevation_at_distance(track, track_distances, distance)
        for distance in line_distances
    ]


def _rdp_vertical(
    points: list[ElevationProfilePoint], epsilon_m: float
) -> list[ElevationProfilePoint]:
    if len(points) <= 2:
        return points

    start = points[0]
    end = points[-1]
    dist_span = end.distance_m - start.distance_m
    max_deviation = 0.0
    max_index = 0
    for index in range(1, len(points) - 1):
        point = points[index]
        if dist_span <= 0:
            deviation = abs(point.elevation_m - start.elevation_m)
        else:
            fraction = (point.distance_m - start.distance_m) / dist_span
            line_ele = start.elevation_m + (end.elevation_m - start.elevation_m) * fraction
            deviation = abs(point.elevation_m - line_ele)
        if deviation > max_deviation:
            max_deviation = deviation
            max_index = index

    if max_deviation <= epsilon_m:
        return [start, end]

    left = _rdp_vertical(points[: max_index + 1], epsilon_m)
    right = _rdp_vertical(points[max_index:], epsilon_m)
    return left[:-1] + right


def _downsample_profile(
    points: list[ElevationProfilePoint],
    max_points: int = ELEVATION_PROFILE_MAX_POINTS,
) -> list[ElevationProfilePoint]:
    if len(points) <= max_points:
        return points

    epsilon = 1.0
    simplified = _rdp_vertical(points, epsilon)
    while len(simplified) > max_points and epsilon < 500:
        epsilon *= 2
        simplified = _rdp_vertical(points, epsilon)

    if len(simplified) <= max_points:
        return simplified

    stride = math.ceil(len(points) / max_points)
    sampled = [points[index] for index in range(0, len(points), stride)]
    if sampled[-1] is not points[-1]:
        sampled.append(points[-1])
    return sampled[:max_points]


def _build_synthesized_profile(
    line_distances: list[float],
    linestring_points: list[Point],
    elevation_min_m: int,
    elevation_max_m: int,
) -> ElevationProfile:
    total = line_distances[-1]
    min_e = float(elevation_min_m)
    max_e = float(elevation_max_m)
    profile: list[ElevationProfilePoint] = []
    for distance, _point in zip(line_distances, linestring_points, strict=True):
        fraction = distance / total
        if len(linestring_points) == 2:
            elevation = min_e + (max_e - min_e) * fraction
        else:
            elevation = min_e + (max_e - min_e) * math.sin(math.pi * fraction)
        profile.append(
            ElevationProfilePoint(
                distance_m=round(distance, 1), elevation_m=int(round(elevation))
            )
        )
    return ElevationProfile(points=tuple(profile), synthesized=True)


def _build_gpx_profile(
    route: Route,
    line_distances: list[float],
    linestring_points: list[Point],
) -> ElevationProfile | None:
    if not route.gpx:
        return None
    try:
        gpx_track = parse_gpx_track_points(route.gpx)
    except GpxValidationError:
        return None

    elevations = _elevations_from_gpx_for_linestring(
        gpx_track, linestring_points, line_distances
    )
    if elevations is None:
        return None

    profile = [
        ElevationProfilePoint(
            distance_m=round(distance, 1),
            elevation_m=elevation,
        )
        for distance, elevation in zip(line_distances, elevations, strict=True)
    ]
    downsampled = _downsample_profile(profile)
    if len(downsampled) < 2:
        return None
    return ElevationProfile(points=tuple(downsampled), synthesized=False)


def build_elevation_profile(route: Route) -> ElevationProfile | None:
    if route.linestring is None or len(route.linestring.points) < 2:
        return None
    if route.elevation_min_m is None or route.elevation_max_m is None:
        return None

    linestring_points = route.linestring.points
    line_distances = _cumulative_distances_for_points(linestring_points)
    if line_distances is None:
        return None

    gpx_profile = _build_gpx_profile(route, line_distances, linestring_points)
    if gpx_profile is not None:
        return gpx_profile

    return _build_synthesized_profile(
        line_distances,
        linestring_points,
        route.elevation_min_m,
        route.elevation_max_m,
    )
