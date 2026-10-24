from __future__ import annotations

import uuid

from app.data.seed_routes_allgaeu import ALLGAEU_CATALOG_SLUGS
from app.data.seed_routes_allgaeu import build_allgaeu_catalog_routes
from app.data.seed_routes_tyrol import TYROL_CATALOG_SLUGS
from app.data.seed_routes_tyrol import build_tyrol_catalog_routes
from app.domain.difficulty import map_difficulty
from app.domain.route import Assessment
from app.domain.route import Completeness
from app.domain.route import LineString
from app.domain.route import Point
from app.domain.route import Provenance
from app.domain.route import Publication
from app.domain.route import Region
from app.domain.route import RegionCoverage
from app.domain.route import Route
from app.domain.route import RouteType
from app.domain.route import TransitAccessibility

SEED_NAMESPACE = uuid.UUID("00000000-0000-4000-8000-000000000010")

PUBLISHED_KLETTERSTEIG_SLUG = "published-klettersteig"
PUBLISHED_ALPINE_HIKE_SLUG = "published-alpine-hike"
PUBLISHED_OUTDOOR_CLIMBING_SLUG = "published-outdoor-climbing"
QUARANTINED_KLETTERSTEIG_SLUG = "quarantined-klettersteig"
QUARANTINED_ALPINE_HIKE_SLUG = "quarantined-alpine-hike"
QUARANTINED_OUTDOOR_CLIMBING_SLUG = "quarantined-outdoor-climbing"

SEED_FIXTURE_SLUGS = (
    PUBLISHED_KLETTERSTEIG_SLUG,
    PUBLISHED_ALPINE_HIKE_SLUG,
    PUBLISHED_OUTDOOR_CLIMBING_SLUG,
    QUARANTINED_KLETTERSTEIG_SLUG,
    QUARANTINED_ALPINE_HIKE_SLUG,
    QUARANTINED_OUTDOOR_CLIMBING_SLUG,
)

SEED_SLUGS = SEED_FIXTURE_SLUGS + ALLGAEU_CATALOG_SLUGS + TYROL_CATALOG_SLUGS

ALLGAEU_LAUNCH_SLUGS = (
    PUBLISHED_KLETTERSTEIG_SLUG,
    PUBLISHED_OUTDOOR_CLIMBING_SLUG,
) + ALLGAEU_CATALOG_SLUGS

TYROL_LAUNCH_SLUGS = TYROL_CATALOG_SLUGS

ALLGAEU = Region(name="Allgäu", country="DE", coverage=RegionCoverage.SUPPORTED)
TYROL = Region(name="Tyrol", country="AT", coverage=RegionCoverage.SUPPORTED)
CHAMONIX = Region(name="Chamonix", country="FR", coverage=RegionCoverage.SAMPLE)

_ALPENVEREIN_LINK = "https://www.alpenverein.de/"


def seed_route_id(slug: str) -> uuid.UUID:
    return uuid.uuid5(SEED_NAMESPACE, slug)


def _hindelanger_geometry() -> tuple[Point, LineString]:
    trailhead = Point(longitude=10.393, latitude=47.498)
    linestring = LineString(
        points=[
            trailhead,
            Point(longitude=10.398, latitude=47.502),
            Point(longitude=10.404, latitude=47.506),
            Point(longitude=10.410, latitude=47.510),
        ]
    )
    return trailhead, linestring


def _hinterstein_blaustein_geometry() -> tuple[Point, LineString]:
    trailhead = Point(longitude=10.445, latitude=47.505)
    linestring = LineString(
        points=[
            trailhead,
            Point(longitude=10.448, latitude=47.508),
            Point(longitude=10.451, latitude=47.511),
        ]
    )
    return trailhead, linestring


def _chamonix_line() -> LineString:
    return LineString(
        points=[
            Point(longitude=6.86, latitude=45.92),
            Point(longitude=6.88, latitude=45.93),
        ]
    )


def _base_route(**overrides: object) -> Route:
    payload: dict[str, object] = {
        "name": "Seed route",
        "route_type": RouteType.ALPINE_HIKE,
        "region": ALLGAEU,
        "publication": Publication.QUARANTINED,
        "trailhead": None,
        "linestring": None,
        "gpx": None,
        "elevation_min_m": None,
        "elevation_max_m": None,
        "elevation_gain_m": None,
        "elevation_loss_m": None,
        "duration_minutes": None,
        "approach_minutes": None,
        "technical_minutes": None,
        "descent_minutes": None,
        "duration_is_estimated": True,
        "original_difficulty_value": None,
        "original_difficulty_scale": None,
        "difficulty": None,
        "closure_assessment": None,
        "season_months": set(),
        "season_note": None,
        "description": "Hand-checked seed example. Not a live catalog entry.",
        "transit_accessibility": TransitAccessibility.UNKNOWN,
        "official_source_links": [],
        "provenance": Provenance.SEED,
        "completeness": Completeness.INCOMPLETE,
        "assessment": Assessment.UNASSESSED,
    }
    payload.update(overrides)
    return Route(**payload)


def build_seed_routes() -> list[tuple[uuid.UUID, Route]]:
    klettersteig_difficulty = map_difficulty(RouteType.KLETTERSTEIG, "K4", "k1_k6")
    alpine_hike_difficulty = map_difficulty(RouteType.ALPINE_HIKE, "T3", "SAC")
    outdoor_climbing_difficulty = map_difficulty(
        RouteType.OUTDOOR_CLIMBING, "6a", "French"
    )
    hindelanger_trailhead, hindelanger_line = _hindelanger_geometry()
    blaustein_trailhead, blaustein_line = _hinterstein_blaustein_geometry()
    chamonix_line = _chamonix_line()

    published_klettersteig = _base_route(
        name="Hindelanger Klettersteig",
        route_type=RouteType.KLETTERSTEIG,
        region=ALLGAEU,
        publication=Publication.PUBLISHED,
        trailhead=hindelanger_trailhead,
        linestring=hindelanger_line,
        elevation_min_m=1220,
        elevation_max_m=1834,
        elevation_gain_m=614,
        elevation_loss_m=614,
        duration_minutes=180,
        approach_minutes=40,
        technical_minutes=90,
        descent_minutes=50,
        original_difficulty_value="K4",
        original_difficulty_scale="k1_k6",
        difficulty=klettersteig_difficulty,
        completeness=Completeness.COMPLETE,
        season_months={6, 7, 8, 9},
        description=(
            "Iconic east-face klettersteig above Bad Hindelang with long cable "
            "sections and a narrow crest finish toward the summit cross."
        ),
        transit_accessibility=TransitAccessibility.TRANSIT_FRIENDLY,
        official_source_links=[_ALPENVEREIN_LINK],
    )
    published_alpine_hike = _base_route(
        name="Seed Published Alpine Hike",
        route_type=RouteType.ALPINE_HIKE,
        region=CHAMONIX,
        publication=Publication.PUBLISHED,
        trailhead=chamonix_line.points[0],
        linestring=chamonix_line,
        elevation_min_m=1000,
        elevation_max_m=1600,
        elevation_gain_m=600,
        elevation_loss_m=600,
        duration_minutes=240,
        original_difficulty_value="T3",
        original_difficulty_scale="SAC",
        difficulty=alpine_hike_difficulty,
        completeness=Completeness.COMPLETE,
        description="Seed example published alpine hike. Not a live catalog entry.",
    )
    published_outdoor_climbing = _base_route(
        name="Blaustein",
        route_type=RouteType.OUTDOOR_CLIMBING,
        region=ALLGAEU,
        publication=Publication.PUBLISHED,
        trailhead=blaustein_trailhead,
        linestring=blaustein_line,
        elevation_min_m=960,
        elevation_max_m=1160,
        elevation_gain_m=200,
        elevation_loss_m=200,
        duration_minutes=120,
        original_difficulty_value="6a",
        original_difficulty_scale="French",
        difficulty=outdoor_climbing_difficulty,
        completeness=Completeness.COMPLETE,
        season_months={5, 6, 7, 8, 9},
        description=(
            "Main Hinterstein limestone sector with long multi-pitch classics "
            "and shorter sport lines on solid grey rock."
        ),
        transit_accessibility=TransitAccessibility.TRANSIT_FRIENDLY,
        official_source_links=[_ALPENVEREIN_LINK],
    )
    quarantined_klettersteig = _base_route(
        name="Seed Quarantined Klettersteig",
        route_type=RouteType.KLETTERSTEIG,
        publication=Publication.QUARANTINED,
        description="Seed example quarantined Klettersteig. Not a live catalog entry.",
    )
    quarantined_alpine_hike = _base_route(
        name="Seed Quarantined Alpine Hike",
        route_type=RouteType.ALPINE_HIKE,
        publication=Publication.QUARANTINED,
        description="Seed example quarantined alpine hike. Not a live catalog entry.",
    )
    quarantined_outdoor_climbing = _base_route(
        name="Seed Quarantined Outdoor Climbing",
        route_type=RouteType.OUTDOOR_CLIMBING,
        publication=Publication.QUARANTINED,
        description="Seed example quarantined outdoor climbing. Not a live catalog entry.",
    )

    fixtures: list[tuple[uuid.UUID, Route]] = [
        (seed_route_id(PUBLISHED_KLETTERSTEIG_SLUG), published_klettersteig),
        (seed_route_id(PUBLISHED_ALPINE_HIKE_SLUG), published_alpine_hike),
        (seed_route_id(PUBLISHED_OUTDOOR_CLIMBING_SLUG), published_outdoor_climbing),
        (seed_route_id(QUARANTINED_KLETTERSTEIG_SLUG), quarantined_klettersteig),
        (seed_route_id(QUARANTINED_ALPINE_HIKE_SLUG), quarantined_alpine_hike),
        (seed_route_id(QUARANTINED_OUTDOOR_CLIMBING_SLUG), quarantined_outdoor_climbing),
    ]
    allgaeu_catalog = build_allgaeu_catalog_routes(_base_route)
    tyrol_catalog = build_tyrol_catalog_routes(_base_route)
    return fixtures + allgaeu_catalog + tyrol_catalog
