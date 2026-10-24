from __future__ import annotations

import uuid
from collections.abc import Callable

from app.domain.difficulty import map_difficulty
from app.domain.route import Completeness
from app.domain.route import LineString
from app.domain.route import Point
from app.domain.route import Publication
from app.domain.route import Route
from app.domain.route import RouteType
from app.domain.route import TransitAccessibility

DOLOMITES_LAUNCH_PUBLISHED_COUNT = 10

DOLOMITES_CATALOG_SLUGS: tuple[str, ...] = (
    "dolomites-pisciadu-via-ferrata",
    "dolomites-innerkofler-de-luca",
    "dolomites-marmolada-ferrata-vin",
    "dolomites-punta-anna-via-ferrata",
    "dolomites-tre-cime-loop",
    "dolomites-monte-pelmo",
    "dolomites-croda-da-lago",
    "dolomites-cinque-torri",
    "dolomites-sasso-di-stria",
    "dolomites-latemar-klettergarten",
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
    from app.data.seed_routes import DOLOMITES
    from app.data.seed_routes import seed_route_id

    trailhead, linestring = _trail_line(trail_lon, trail_lat, *path)
    difficulty = map_difficulty(RouteType.KLETTERSTEIG, diff_value, diff_scale)
    route = base_route(
        name=name,
        route_type=RouteType.KLETTERSTEIG,
        region=DOLOMITES,
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
    from app.data.seed_routes import DOLOMITES
    from app.data.seed_routes import seed_route_id

    trailhead, linestring = _trail_line(trail_lon, trail_lat, *path)
    difficulty = map_difficulty(RouteType.ALPINE_HIKE, diff_value, "SAC")
    route = base_route(
        name=name,
        route_type=RouteType.ALPINE_HIKE,
        region=DOLOMITES,
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
    from app.data.seed_routes import DOLOMITES
    from app.data.seed_routes import seed_route_id

    trailhead, linestring = _trail_line(trail_lon, trail_lat, *path)
    difficulty = map_difficulty(RouteType.OUTDOOR_CLIMBING, diff_value, diff_scale)
    route = base_route(
        name=name,
        route_type=RouteType.OUTDOOR_CLIMBING,
        region=DOLOMITES,
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


def build_dolomites_catalog_routes(
    base_route: Callable[..., Route],
) -> list[tuple[uuid.UUID, Route]]:
    cai_link = "https://www.cai.it/"
    entries: list[tuple[uuid.UUID, Route]] = [
        _klettersteig_entry(
            base_route,
            slug="dolomites-pisciadu-via-ferrata",
            name="Pisciadù Via Ferrata",
            diff_value="C",
            diff_scale="huebler",
            trail_lon=11.852,
            trail_lat=46.518,
            path=((11.856, 46.522), (11.860, 46.526)),
            elev_min=2540,
            elev_max=2985,
            gain=445,
            duration=300,
            approach=90,
            technical=150,
            descent=60,
            description=(
                "Classic north-face via ferrata on the Pisciadù tower in the "
                "Sella group with steep ladders and a narrow summit ridge."
            ),
            transit=TransitAccessibility.LIMITED,
            link=cai_link,
        ),
        _klettersteig_entry(
            base_route,
            slug="dolomites-innerkofler-de-luca",
            name="Innerkofler-De Luca",
            diff_value="K3",
            diff_scale="k1_k6",
            trail_lon=12.302,
            trail_lat=46.618,
            path=((12.306, 46.622), (12.310, 46.626)),
            elev_min=2320,
            elev_max=2999,
            gain=679,
            duration=420,
            approach=120,
            technical=180,
            descent=120,
            description=(
                "Normal route on the south face of Monte Paterno linking the "
                "Tre Cime area with long cable sections and tunnel passages."
            ),
            transit=TransitAccessibility.LIMITED,
            link=cai_link,
        ),
        _klettersteig_entry(
            base_route,
            slug="dolomites-marmolada-ferrata-vin",
            name="Ferrata Vin (Marmolada)",
            diff_value="K4",
            diff_scale="k1_k6",
            trail_lon=11.968,
            trail_lat=46.438,
            path=((11.972, 46.442), (11.976, 46.446)),
            elev_min=2050,
            elev_max=3343,
            gain=1293,
            duration=540,
            approach=180,
            technical=240,
            descent=120,
            description=(
                "High alpine west-ridge ferrata on the Marmolada with glacier "
                "approach and sustained exposure on the Queen of the Dolomites."
            ),
            transit=TransitAccessibility.LIMITED,
            link=cai_link,
            season_months={6, 7, 8},
        ),
        _klettersteig_entry(
            base_route,
            slug="dolomites-punta-anna-via-ferrata",
            name="Punta Anna Via Ferrata",
            diff_value="D",
            diff_scale="huebler",
            trail_lon=12.058,
            trail_lat=46.528,
            path=((12.062, 46.532), (12.066, 46.536)),
            elev_min=2320,
            elev_max=2738,
            gain=418,
            duration=360,
            approach=90,
            technical=180,
            descent=90,
            description=(
                "Exposed east-ridge ferrata on the Tofane above Cortina with "
                "steep chimneys and panoramic views toward the Cristallo group."
            ),
            transit=TransitAccessibility.TRANSIT_FRIENDLY,
            link=cai_link,
        ),
        _alpine_hike_entry(
            base_route,
            slug="dolomites-tre-cime-loop",
            name="Tre Cime di Lavaredo Loop",
            diff_value="T2",
            trail_lon=12.303,
            trail_lat=46.619,
            path=((12.307, 46.623), (12.311, 46.627)),
            elev_min=2320,
            elev_max=2454,
            gain=400,
            duration=300,
            description=(
                "Iconic circuit around the Tre Cime towers from Rifugio Auronzo "
                "with well-marked paths and short secured sections."
            ),
            transit=TransitAccessibility.LIMITED,
            link=cai_link,
        ),
        _alpine_hike_entry(
            base_route,
            slug="dolomites-monte-pelmo",
            name="Monte Pelmo",
            diff_value="T4",
            trail_lon=12.128,
            trail_lat=46.418,
            path=((12.132, 46.422), (12.136, 46.426)),
            elev_min=1850,
            elev_max=3168,
            gain=1318,
            duration=600,
            description=(
                "Major summit in the Zoldo Dolomites via the northwest spur; "
                "long hut approach and blocky terrain on the upper ridge."
            ),
            transit=TransitAccessibility.LIMITED,
            link=cai_link,
            season_months={6, 7, 8, 9},
        ),
        _alpine_hike_entry(
            base_route,
            slug="dolomites-croda-da-lago",
            name="Croda da Lago",
            diff_value="T3",
            trail_lon=12.058,
            trail_lat=46.488,
            path=((12.062, 46.492), (12.066, 46.496)),
            elev_min=2040,
            elev_max=2701,
            gain=661,
            duration=420,
            description=(
                "Cortina-area classic from Rifugio Palmieri with a steep grass "
                "slope and rocky summit block above Lake Federa."
            ),
            transit=TransitAccessibility.TRANSIT_FRIENDLY,
            link=cai_link,
        ),
        _outdoor_climbing_entry(
            base_route,
            slug="dolomites-cinque-torri",
            name="Cinque Torri",
            diff_value="6a",
            diff_scale="French",
            trail_lon=12.068,
            trail_lat=46.512,
            path=((12.070, 46.514), (12.072, 46.516)),
            elev_min=2250,
            elev_max=2365,
            gain=200,
            duration=240,
            description=(
                "Historic open-air climbing museum near Cortina with short "
                "multi-pitch routes on pale dolomite towers."
            ),
            transit=TransitAccessibility.TRANSIT_FRIENDLY,
            link=cai_link,
        ),
        _outdoor_climbing_entry(
            base_route,
            slug="dolomites-sasso-di-stria",
            name="Sasso di Stria",
            diff_value="6b",
            diff_scale="French",
            trail_lon=11.978,
            trail_lat=46.508,
            path=((11.980, 46.510), (11.982, 46.512)),
            elev_min=2180,
            elev_max=2440,
            gain=260,
            duration=300,
            description=(
                "Lagazuoi-area limestone wall with long alpine sport and trad "
                "lines above the Falzarego pass."
            ),
            transit=TransitAccessibility.LIMITED,
            link=cai_link,
        ),
        _outdoor_climbing_entry(
            base_route,
            slug="dolomites-latemar-klettergarten",
            name="Latemar Klettergarten",
            diff_value="V",
            diff_scale="UIAA",
            trail_lon=11.578,
            trail_lat=46.378,
            path=((11.580, 46.380), (11.582, 46.382)),
            elev_min=1680,
            elev_max=1880,
            gain=200,
            duration=210,
            description=(
                "Sunny sectors on the Latemar massif with well-bolted single- "
                "pitch routes on compact dolomitic rock above Obereggen."
            ),
            transit=TransitAccessibility.LIMITED,
            link=cai_link,
        ),
    ]
    assert len(entries) == len(DOLOMITES_CATALOG_SLUGS)
    return entries
