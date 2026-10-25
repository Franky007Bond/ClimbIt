from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass

from app.domain.route import LineString
from app.domain.route import Point

GPX_NS = "http://www.topografix.com/GPX/1/1"
GPX_DEFAULT_DESCRIPTION = "No description was provided for this GPX upload."


class GpxValidationError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ProcessedGpx:
    linestring: LineString
    trailhead: Point
    gpx_xml: str
    elevation_min_m: int | None
    elevation_max_m: int | None
    elevation_gain_m: int | None
    elevation_loss_m: int | None


def _local_name(tag: str) -> str:
    if tag.startswith("{"):
        return tag.split("}", 1)[1]
    return tag


def _child_elements(parent: ET.Element, local: str) -> list[ET.Element]:
    return [child for child in parent if _local_name(child.tag) == local]


def _text_content(element: ET.Element) -> str:
    return (element.text or "").strip()


def _parse_trkpt(trkpt: ET.Element) -> tuple[float, float, float | None]:
    lat_raw = trkpt.get("lat")
    lon_raw = trkpt.get("lon")
    if lat_raw is None or lon_raw is None:
        raise GpxValidationError("track point missing lat or lon")
    try:
        latitude = float(lat_raw)
        longitude = float(lon_raw)
    except ValueError as exc:
        raise GpxValidationError("track point lat or lon is not numeric") from exc
    elevation: float | None = None
    for child in trkpt:
        if _local_name(child.tag) == "ele":
            try:
                elevation = float(_text_content(child))
            except ValueError as exc:
                raise GpxValidationError(
                    "track point elevation is not numeric"
                ) from exc
            break
    return longitude, latitude, elevation


def _collect_trk_points(trk: ET.Element) -> list[tuple[float, float, float | None]]:
    points: list[tuple[float, float, float | None]] = []
    for trkseg in _child_elements(trk, "trkseg"):
        for trkpt in _child_elements(trkseg, "trkpt"):
            points.append(_parse_trkpt(trkpt))
    for trkpt in _child_elements(trk, "trkpt"):
        points.append(_parse_trkpt(trkpt))
    return points


def _choose_track(root: ET.Element) -> list[tuple[float, float, float | None]]:
    tracks = [element for element in root.iter() if _local_name(element.tag) == "trk"]
    if not tracks:
        raise GpxValidationError("no track found")
    best: list[tuple[float, float, float | None]] | None = None
    for trk in tracks:
        points = _collect_trk_points(trk)
        if best is None or len(points) > len(best):
            best = points
    assert best is not None
    if len(best) < 2:
        raise GpxValidationError("track must contain at least two track points")
    return best


def _elevation_stats(
    points: list[tuple[float, float, float | None]],
) -> tuple[int | None, int | None, int | None, int | None]:
    elevations = [ele for _, _, ele in points if ele is not None]
    if len(elevations) != len(points):
        return None, None, None, None
    rounded = [int(round(value)) for value in elevations]
    gain = 0
    loss = 0
    for previous, current in zip(rounded, rounded[1:], strict=False):
        delta = current - previous
        if delta > 0:
            gain += delta
        elif delta < 0:
            loss += -delta
    return min(rounded), max(rounded), gain, loss


def _build_sanitized_gpx(points: list[tuple[float, float, float | None]]) -> str:
    ET.register_namespace("", GPX_NS)
    gpx = ET.Element(
        f"{{{GPX_NS}}}gpx",
        {"version": "1.1", "creator": "ClimbIt"},
    )
    trk = ET.SubElement(gpx, f"{{{GPX_NS}}}trk")
    trkseg = ET.SubElement(trk, f"{{{GPX_NS}}}trkseg")
    for longitude, latitude, elevation in points:
        lat_text = f"{latitude:.8f}".rstrip("0").rstrip(".")
        lon_text = f"{longitude:.8f}".rstrip("0").rstrip(".")
        trkpt = ET.SubElement(
            trkseg,
            f"{{{GPX_NS}}}trkpt",
            {"lat": lat_text, "lon": lon_text},
        )
        if elevation is not None:
            ele = ET.SubElement(trkpt, f"{{{GPX_NS}}}ele")
            ele.text = str(elevation)
    return ET.tostring(gpx, encoding="unicode", xml_declaration=True)


def _reject_unsafe_xml(raw: bytes) -> None:
    if not raw.strip():
        raise GpxValidationError("empty file")
    snippet = raw[:1024].lower()
    if b"<!doctype" in snippet or b"<!entity" in snippet:
        raise GpxValidationError("document type declarations are not allowed")


def parse_gpx_track_points(gpx_xml: str) -> list[tuple[float, float, float | None]]:
    try:
        root = ET.fromstring(gpx_xml)
    except ET.ParseError as exc:
        raise GpxValidationError("malformed XML") from exc
    return _choose_track(root)


def process_gpx_upload(raw: bytes) -> ProcessedGpx:
    _reject_unsafe_xml(raw)
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise GpxValidationError("malformed XML") from exc

    points = _choose_track(root)
    line_points = [
        Point(longitude=longitude, latitude=latitude)
        for longitude, latitude, _ in points
    ]
    linestring = LineString(points=line_points)
    trailhead = line_points[0]
    ele_min, ele_max, gain, loss = _elevation_stats(points)
    gpx_xml = _build_sanitized_gpx(points)
    return ProcessedGpx(
        linestring=linestring,
        trailhead=trailhead,
        gpx_xml=gpx_xml,
        elevation_min_m=ele_min,
        elevation_max_m=ele_max,
        elevation_gain_m=gain,
        elevation_loss_m=loss,
    )
