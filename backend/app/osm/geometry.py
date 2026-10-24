from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domain.route import LineString
from app.domain.route import Point


class OsmGeometryError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ParsedOsmGeometry:
    linestring: LineString
    trailhead: Point
    elevation_min_m: int | None
    elevation_max_m: int | None
    elevation_gain_m: int | None
    elevation_loss_m: int | None


def _elevation_stats(
    elevations: list[float | None],
) -> tuple[int | None, int | None, int | None, int | None]:
    if not elevations or any(value is None for value in elevations):
        return None, None, None, None
    rounded = [int(round(value)) for value in elevations if value is not None]
    gain = 0
    loss = 0
    for previous, current in zip(rounded, rounded[1:], strict=False):
        delta = current - previous
        if delta > 0:
            gain += delta
        elif delta < 0:
            loss += -delta
    return min(rounded), max(rounded), gain, loss


def _node_elevation(node: dict[str, Any]) -> float | None:
    tags = node.get("tags")
    if isinstance(tags, dict) and "ele" in tags:
        try:
            return float(str(tags["ele"]).strip())
        except ValueError:
            return None
    if "ele" in node:
        try:
            return float(str(node["ele"]).strip())
        except ValueError:
            return None
    return None


def _geometry_points(
    element: dict[str, Any],
    elements_by_id: dict[tuple[str, int], dict[str, Any]],
) -> list[tuple[float, float, float | None]]:
    geometry = element.get("geometry")
    if isinstance(geometry, list) and geometry:
        points: list[tuple[float, float, float | None]] = []
        for item in geometry:
            if not isinstance(item, dict):
                continue
            lat = item.get("lat")
            lon = item.get("lon")
            if lat is None or lon is None:
                continue
            try:
                latitude = float(lat)
                longitude = float(lon)
            except (TypeError, ValueError):
                continue
            elevation = _node_elevation(item)
            points.append((longitude, latitude, elevation))
        if points:
            return points

    nodes = element.get("nodes")
    if isinstance(nodes, list):
        points = []
        for node_id in nodes:
            if not isinstance(node_id, int):
                continue
            node = elements_by_id.get(("node", node_id))
            if node is None:
                continue
            lat = node.get("lat")
            lon = node.get("lon")
            if lat is None or lon is None:
                continue
            try:
                latitude = float(lat)
                longitude = float(lon)
            except (TypeError, ValueError):
                continue
            points.append((longitude, latitude, _node_elevation(node)))
        return points

    return []


def parse_overpass_geometry(
    payload: dict[str, Any],
    *,
    osm_type: str,
    osm_id: int,
) -> ParsedOsmGeometry:
    elements = payload.get("elements")
    if not isinstance(elements, list):
        msg = "Overpass response missing elements array"
        raise OsmGeometryError(msg)

    elements_by_id: dict[tuple[str, int], dict[str, Any]] = {}
    for item in elements:
        if not isinstance(item, dict):
            continue
        item_type = item.get("type")
        item_id = item.get("id")
        if isinstance(item_type, str) and isinstance(item_id, int):
            elements_by_id[(item_type, item_id)] = item

    target = elements_by_id.get((osm_type, osm_id))
    if target is None:
        msg = f"Overpass response missing {osm_type} {osm_id}"
        raise OsmGeometryError(msg)

    raw_points = _geometry_points(target, elements_by_id)
    if len(raw_points) < 2:
        msg = f"{osm_type} {osm_id} has fewer than two coordinates"
        raise OsmGeometryError(msg)

    line_points = [
        Point(longitude=longitude, latitude=latitude)
        for longitude, latitude, _ in raw_points
    ]
    elevations = [ele for _, _, ele in raw_points]
    ele_min, ele_max, gain, loss = _elevation_stats(elevations)
    return ParsedOsmGeometry(
        linestring=LineString(points=line_points),
        trailhead=line_points[0],
        elevation_min_m=ele_min,
        elevation_max_m=ele_max,
        elevation_gain_m=gain,
        elevation_loss_m=loss,
    )
