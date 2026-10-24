from __future__ import annotations

import uuid
from collections.abc import Callable

from app.domain.difficulty import map_difficulty
from app.domain.route import Completeness
from app.domain.route import LineString
from app.domain.route import Point
from app.domain.route import Publication
from app.domain.route import Region
from app.domain.route import Route
from app.domain.route import RouteType
from app.domain.route import TransitAccessibility

FRENCH_SWISS_LAUNCH_PUBLISHED_COUNT = 5

FRENCH_SWISS_CATALOG_SLUGS: tuple[str, ...] = (
    "fr-ch-arête-des-cosmiques",
    "fr-ch-edelweiss-ferrata",
    "fr-ch-five-lakes-walk",
    "fr-ch-grimsel-sport-climbing",
)


def _trail_line(
    trail_lon: float,
    trail_lat: float,
    *path: tuple[float, float],
) -> tuple[Point, LineString]:
    trailhead = Point(longitude=trail_lon, latitude=trail_lat)
    points = [trailhead] + [Point(longitude=lon, latitude=lat) for lon, lat in path]
    return trailhead, LineString(points=points)


def _summer() -> set[int]:
    return {6, 7, 8, 9}


def _klettersteig_entry(
    base_route: Callable[..., Route],
    *,
    slug: str,
    name: str,
    region: Region,
    diff_value: str,
    diff_scale: str,
    trail_lon: float,
    trail_lat: float,
    path: tuple[tuple[float, float], ...],
    elev_min: int,
    elev_max: int,
    gain: int,
    duration: int,
    approach: int,
    technical: int,
    descent: int,
    description: str,
    transit: TransitAccessibility,
    link: str,
    season_months: set[int] | None = None,
) -> tuple[uuid.UUID, Route]:
    from app.data.seed_routes import seed_route_id

    trailhead, linestring = _trail_line(trail_lon, trail_lat, *path)
    difficulty = map_difficulty(RouteType.KLETTERSTEIG, diff_value, diff_scale)
    route = base_route(
        name=name,
        route_type=RouteType.KLETTERSTEIG,
        region=region,
        publication=Publication.PUBLISHED,
        trailhead=trailhead,
        linestring=linestring,
        elevation_min_m=elev_min,
        elevation_max_m=elev_max,
        elevation_gain_m=gain,
        elevation_loss_m=gain,
        duration_minutes=duration,
        approach_minutes=approach,
        technical_minutes=technical,
        descent_minutes=descent,
        original_difficulty_value=diff_value,
        original_difficulty_scale=diff_scale,
        difficulty=difficulty,
        completeness=Completeness.COMPLETE,
        season_months=season_months or _summer(),
        description=description,
        transit_accessibility=transit,
        official_source_links=[link],
    )
    return seed_route_id(slug), route


def _alpine_hike_entry(
    base_route: Callable[..., Route],
    *,
    slug: str,
    name: str,
    region: Region,
    diff_value: str,
    trail_lon: float,
    trail_lat: float,
    path: tuple[tuple[float, float], ...],
    elev_min: int,
    elev_max: int,
    gain: int,
    duration: int,
    description: str,
    transit: TransitAccessibility,
    link: str,
    season_months: set[int] | None = None,
) -> tuple[uuid.UUID, Route]:
    from app.data.seed_routes import seed_route_id

    trailhead, linestring = _trail_line(trail_lon, trail_lat, *path)
    difficulty = map_difficulty(RouteType.ALPINE_HIKE, diff_value, "SAC")
    route = base_route(
        name=name,
        route_type=RouteType.ALPINE_HIKE,
        region=region,
        publication=Publication.PUBLISHED,
        trailhead=trailhead,
        linestring=linestring,
        elevation_min_m=elev_min,
        elevation_max_m=elev_max,
        elevation_gain_m=gain,
        elevation_loss_m=gain,
        duration_minutes=duration,
        original_difficulty_value=diff_value,
        original_difficulty_scale="SAC",
        difficulty=difficulty,
        completeness=Completeness.COMPLETE,
        season_months=season_months or _summer(),
        description=description,
        transit_accessibility=transit,
        official_source_links=[link],
    )
    return seed_route_id(slug), route


def _outdoor_climbing_entry(
    base_route: Callable[..., Route],
    *,
    slug: str,
    name: str,
    region: Region,
    diff_value: str,
    diff_scale: str,
    trail_lon: float,
    trail_lat: float,
    path: tuple[tuple[float, float], ...],
    elev_min: int,
    elev_max: int,
    gain: int,
    duration: int,
    description: str,
    transit: TransitAccessibility,
    link: str,
    season_months: set[int] | None = None,
) -> tuple[uuid.UUID, Route]:
    from app.data.seed_routes import seed_route_id

    trailhead, linestring = _trail_line(trail_lon, trail_lat, *path)
    difficulty = map_difficulty(RouteType.OUTDOOR_CLIMBING, diff_value, diff_scale)
    route = base_route(
        name=name,
        route_type=RouteType.OUTDOOR_CLIMBING,
        region=region,
        publication=Publication.PUBLISHED,
        trailhead=trailhead,
        linestring=linestring,
        elevation_min_m=elev_min,
        elevation_max_m=elev_max,
        elevation_gain_m=gain,
        elevation_loss_m=gain,
        duration_minutes=duration,
        original_difficulty_value=diff_value,
        original_difficulty_scale=diff_scale,
        difficulty=difficulty,
        completeness=Completeness.COMPLETE,
        season_months=season_months or {5, 6, 7, 8, 9},
        description=description,
        transit_accessibility=transit,
        official_source_links=[link],
    )
    return seed_route_id(slug), route


def build_french_swiss_catalog_routes(
    base_route: Callable[..., Route],
) -> list[tuple[uuid.UUID, Route]]:
    from app.data.seed_routes import CHAMONIX
    from app.data.seed_routes import GRIMSEL
    from app.data.seed_routes import ZERMATT

    ffme_link = "https://www.ffme.fr/"
    sac_link = "https://www.sac-cas.ch/"
    entries: list[tuple[uuid.UUID, Route]] = [
        _klettersteig_entry(
            base_route,
            slug="fr-ch-arête-des-cosmiques",
            name="Arête des Cosmiques",
            region=CHAMONIX,
            diff_value="K3",
            diff_scale="k1_k6",
            trail_lon=6.872,
            trail_lat=45.879,
            path=((6.876, 45.883), (6.880, 45.887)),
            elev_min=3842,
            elev_max=3842,
            gain=120,
            duration=240,
            approach=60,
            technical=120,
            descent=60,
            description=(
                "Classic mixed ridge above the Aiguille du Midi with short "
                "exposed steps and glacier approach from the téléphérique."
            ),
            transit=TransitAccessibility.TRANSIT_FRIENDLY,
            link=ffme_link,
            season_months={6, 7, 8},
        ),
        _klettersteig_entry(
            base_route,
            slug="fr-ch-edelweiss-ferrata",
            name="Edelweiss Via Ferrata",
            region=ZERMATT,
            diff_value="K3",
            diff_scale="k1_k6",
            trail_lon=7.748,
            trail_lat=46.020,
            path=((7.752, 46.024), (7.756, 46.028)),
            elev_min=1680,
            elev_max=2180,
            gain=500,
            duration=300,
            approach=90,
            technical=150,
            descent=60,
            description=(
                "Sunny south-facing ferrata above Zermatt with ladders and "
                "cables on compact gneiss above the Findeln hamlet."
            ),
            transit=TransitAccessibility.TRANSIT_FRIENDLY,
            link=sac_link,
        ),
        _alpine_hike_entry(
            base_route,
            slug="fr-ch-five-lakes-walk",
            name="Five Lakes Walk",
            region=ZERMATT,
            diff_value="T2",
            trail_lon=7.758,
            trail_lat=46.008,
            path=((7.762, 46.012), (7.766, 46.016)),
            elev_min=1970,
            elev_max=2547,
            gain=577,
            duration=300,
            description=(
                "Scenic Matterhorn-facing circuit past alpine lakes with "
                "well-marked paths and short rocky steps near the cols."
            ),
            transit=TransitAccessibility.TRANSIT_FRIENDLY,
            link=sac_link,
        ),
        _outdoor_climbing_entry(
            base_route,
            slug="fr-ch-grimsel-sport-climbing",
            name="Grimsel Sport Climbing",
            region=GRIMSEL,
            diff_value="6a",
            diff_scale="French",
            trail_lon=8.328,
            trail_lat=46.558,
            path=((8.330, 46.560), (8.332, 46.562)),
            elev_min=1920,
            elev_max=1980,
            gain=60,
            duration=180,
            description=(
                "Compact granite slabs and corners above the Grimsel pass with "
                "well-bolted single-pitch sport lines in a high-alpine setting."
            ),
            transit=TransitAccessibility.LIMITED,
            link=sac_link,
        ),
    ]
    assert len(entries) == len(FRENCH_SWISS_CATALOG_SLUGS)
    return entries
