from __future__ import annotations

import uuid
from datetime import datetime
from datetime import timezone

from app.domain.route import Assessment
from app.domain.route import Completeness
from app.domain.route import Provenance
from app.domain.route import Publication
from app.domain.route import Region
from app.domain.route import RegionCoverage
from app.domain.route import Route
from app.domain.route import TransitAccessibility
from app.osm.geometry import ParsedOsmGeometry
from app.osm.manifest import ManifestEntry

OSM_IMPORT_NAMESPACE = uuid.UUID("00000000-0000-4000-8000-000000000020")

OSM_COPYRIGHT_URL = "https://www.openstreetmap.org/copyright"


def osm_route_id(osm_type: str, osm_id: int) -> uuid.UUID:
    return uuid.uuid5(OSM_IMPORT_NAMESPACE, f"{osm_type}/{osm_id}")


def osm_object_url(osm_type: str, osm_id: int) -> str:
    return f"https://www.openstreetmap.org/{osm_type}/{osm_id}"


def format_import_description(imported_at: datetime) -> str:
    timestamp = imported_at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return (
        f"Imported from OpenStreetMap at {timestamp} UTC. © OpenStreetMap contributors"
    )


def build_osm_import_route(
    *,
    entry: ManifestEntry,
    geometry: ParsedOsmGeometry,
    imported_at: datetime,
    publication: Publication = Publication.QUARANTINED,
) -> Route:
    if publication is not Publication.QUARANTINED:
        msg = "OSM import routes must remain quarantined"
        raise ValueError(msg)

    region = Region(
        name=entry.region_name,
        country=entry.region_country,
        coverage=RegionCoverage.UNSUPPORTED,
    )
    duration_minutes = entry.duration_minutes
    duration_is_estimated = duration_minutes is not None

    return Route(
        name=entry.name,
        route_type=entry.route_type,
        region=region,
        publication=Publication.QUARANTINED,
        trailhead=geometry.trailhead,
        linestring=geometry.linestring,
        gpx=None,
        elevation_min_m=geometry.elevation_min_m,
        elevation_max_m=geometry.elevation_max_m,
        elevation_gain_m=geometry.elevation_gain_m,
        elevation_loss_m=geometry.elevation_loss_m,
        duration_minutes=duration_minutes,
        approach_minutes=None,
        technical_minutes=None,
        descent_minutes=None,
        duration_is_estimated=duration_is_estimated,
        original_difficulty_value=None,
        original_difficulty_scale=None,
        difficulty=None,
        closure_assessment=None,
        season_months=set(),
        season_note=None,
        description=format_import_description(imported_at),
        transit_accessibility=TransitAccessibility.UNKNOWN,
        official_source_links=[
            OSM_COPYRIGHT_URL,
            osm_object_url(entry.osm_type.value, entry.osm_id),
        ],
        provenance=Provenance.OSM,
        completeness=Completeness.INCOMPLETE,
        assessment=Assessment.UNASSESSED,
    )
