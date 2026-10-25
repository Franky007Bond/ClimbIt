from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from app.domain.route import LineString
from app.domain.route import Point
from app.gpx.process import ProcessedGpx
from app.gpx.process import process_gpx_upload

_GPX_DIR = Path(__file__).resolve().parent / "gpx"


@lru_cache
def load_seed_gpx(name: str) -> ProcessedGpx:
    return process_gpx_upload((_GPX_DIR / name).read_bytes())


def seed_gpx_geometry(name: str) -> tuple[Point, LineString, str]:
    processed = load_seed_gpx(name)
    return processed.trailhead, processed.linestring, processed.gpx_xml
