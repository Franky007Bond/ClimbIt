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

TYROL_LAUNCH_PUBLISHED_COUNT = 15

TYROL_CATALOG_SLUGS: tuple[str, ...] = (
    "tyrol-innsbrucker-klettersteig",
    "tyrol-stripsenjoch-klettersteig",
    "tyrol-mieminger-klettersteig",
    "tyrol-olperer-klettersteig",
    "tyrol-dalfazer-wasserfallsteig",
    "tyrol-wildspitze",
    "tyrol-grossvenediger",
    "tyrol-pfeiserspitze",
    "tyrol-hochfeiler",
    "tyrol-grosser-troegler",
    "tyrol-elferwand",
    "tyrol-lixwerk",
    "tyrol-schlick-klettergarten",
    "tyrol-karwendel-woerndle",
    "tyrol-meiler-platt",
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
    from app.data.seed_routes import TYROL
    from app.data.seed_routes import seed_route_id

    trailhead, linestring = _trail_line(trail_lon, trail_lat, *path)
    difficulty = map_difficulty(RouteType.KLETTERSTEIG, diff_value, diff_scale)
    route = base_route(
        name=name,
        route_type=RouteType.KLETTERSTEIG,
        region=TYROL,
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
    from app.data.seed_routes import TYROL
    from app.data.seed_routes import seed_route_id

    trailhead, linestring = _trail_line(trail_lon, trail_lat, *path)
    difficulty = map_difficulty(RouteType.ALPINE_HIKE, diff_value, "SAC")
    route = base_route(
        name=name,
        route_type=RouteType.ALPINE_HIKE,
        region=TYROL,
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
    from app.data.seed_routes import TYROL
    from app.data.seed_routes import seed_route_id

    trailhead, linestring = _trail_line(trail_lon, trail_lat, *path)
    difficulty = map_difficulty(RouteType.OUTDOOR_CLIMBING, diff_value, diff_scale)
    route = base_route(
        name=name,
        route_type=RouteType.OUTDOOR_CLIMBING,
        region=TYROL,
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


def build_tyrol_catalog_routes(
    base_route: Callable[..., Route],
) -> list[tuple[uuid.UUID, Route]]:
    av_at_link = "https://www.alpenverein.at/"
    entries: list[tuple[uuid.UUID, Route]] = [
        _klettersteig_entry(
            base_route,
            slug="tyrol-innsbrucker-klettersteig",
            name="Innsbrucker Klettersteig",
            diff_value="K3",
            diff_scale="k1_k6",
            trail_lon=11.382,
            trail_lat=47.308,
            path=((11.386, 47.312), (11.390, 47.316)),
            elev_min=1900,
            elev_max=2334,
            gain=434,
            duration=240,
            approach=60,
            technical=120,
            descent=60,
            description=(
                "Classic north-ridge via ferrata above Innsbruck from the Hafelekar "
                "area with long airy sections and views over the Inn valley."
            ),
            transit=TransitAccessibility.TRANSIT_FRIENDLY,
            link=av_at_link,
        ),
        _klettersteig_entry(
            base_route,
            slug="tyrol-stripsenjoch-klettersteig",
            name="Stripsenjoch Klettersteig",
            diff_value="K3",
            diff_scale="k1_k6",
            trail_lon=12.118,
            trail_lat=47.478,
            path=((12.122, 47.482), (12.126, 47.486)),
            elev_min=1180,
            elev_max=1577,
            gain=397,
            duration=300,
            approach=90,
            technical=120,
            descent=90,
            description=(
                "Exposed east-ridge route in the Kaisergebirge with steep ladders "
                "and cables above the Stripsenjoch saddle."
            ),
            transit=TransitAccessibility.LIMITED,
            link=av_at_link,
        ),
        _klettersteig_entry(
            base_route,
            slug="tyrol-mieminger-klettersteig",
            name="Mieminger Klettersteig",
            diff_value="K4",
            diff_scale="k1_k6",
            trail_lon=10.978,
            trail_lat=47.342,
            path=((10.982, 47.346), (10.986, 47.350)),
            elev_min=1520,
            elev_max=2745,
            gain=1225,
            duration=480,
            approach=120,
            technical=240,
            descent=120,
            description=(
                "Long west-ridge traverse on the Mieminger Chain with sustained "
                "exposure and several re-ascents along the crest."
            ),
            transit=TransitAccessibility.LIMITED,
            link=av_at_link,
        ),
        _klettersteig_entry(
            base_route,
            slug="tyrol-olperer-klettersteig",
            name="Olperer Klettersteig",
            diff_value="K2",
            diff_scale="k1_k6",
            trail_lon=11.728,
            trail_lat=47.042,
            path=((11.732, 47.046), (11.736, 47.050)),
            elev_min=1780,
            elev_max=3476,
            gain=1696,
            duration=540,
            approach=180,
            technical=240,
            descent=120,
            description=(
                "High alpine via ferrata on the Olperer above the Schlegeis reservoir "
                "in the Zillertal; often combined with hut nights."
            ),
            transit=TransitAccessibility.LIMITED,
            link=av_at_link,
        ),
        _klettersteig_entry(
            base_route,
            slug="tyrol-dalfazer-wasserfallsteig",
            name="Dalfazer Wasserfallsteig",
            diff_value="K3",
            diff_scale="k1_k6",
            trail_lon=11.862,
            trail_lat=47.238,
            path=((11.866, 47.242), (11.870, 47.246)),
            elev_min=620,
            elev_max=1420,
            gain=800,
            duration=330,
            approach=75,
            technical=180,
            descent=75,
            description=(
                "Waterfall-side secured path in the Zillertal with ladders and "
                "bridges beside the Dalfaz waterfall near Lake Achensee."
            ),
            transit=TransitAccessibility.TRANSIT_FRIENDLY,
            link=av_at_link,
        ),
        _alpine_hike_entry(
            base_route,
            slug="tyrol-wildspitze",
            name="Wildspitze",
            diff_value="T4",
            trail_lon=10.918,
            trail_lat=46.968,
            path=((10.922, 46.972), (10.926, 46.976)),
            elev_min=2670,
            elev_max=3774,
            gain=1104,
            duration=600,
            description=(
                "Highest peak in Tyrol via the Mötzferner or Breslauer Hut routes; "
                "glacier travel and alpine experience required on summit day."
            ),
            transit=TransitAccessibility.LIMITED,
            link=av_at_link,
            season_months={6, 7, 8},
        ),
        _alpine_hike_entry(
            base_route,
            slug="tyrol-grossvenediger",
            name="Großvenediger",
            diff_value="T4",
            trail_lon=12.342,
            trail_lat=47.108,
            path=((12.346, 47.112), (12.350, 47.116)),
            elev_min=2300,
            elev_max=3666,
            gain=1366,
            duration=660,
            description=(
                "Major glaciated summit in the Venediger group; hut-based ascent "
                "from Matrei or Prägraten with crevasse terrain on the upper glacier."
            ),
            transit=TransitAccessibility.LIMITED,
            link=av_at_link,
            season_months={6, 7, 8},
        ),
        _alpine_hike_entry(
            base_route,
            slug="tyrol-pfeiserspitze",
            name="Pfeiserspitze",
            diff_value="T3",
            trail_lon=11.438,
            trail_lat=47.312,
            path=((11.442, 47.316), (11.446, 47.320)),
            elev_min=920,
            elev_max=1922,
            gain=1002,
            duration=420,
            description=(
                "Karwendel classic from the Pfeiserscharte area with steep grass "
                "slopes and a rocky summit block above Hall in Tirol."
            ),
            transit=TransitAccessibility.TRANSIT_FRIENDLY,
            link=av_at_link,
        ),
        _alpine_hike_entry(
            base_route,
            slug="tyrol-hochfeiler",
            name="Hochfeiler",
            diff_value="T3",
            trail_lon=12.148,
            trail_lat=47.052,
            path=((12.152, 47.056), (12.156, 47.060)),
            elev_min=1520,
            elev_max=3510,
            gain=1990,
            duration=540,
            description=(
                "Dominant Zillertal Alps summit on the Italian border; long hut "
                "approach and blocky terrain on the normal route from the Berliner Hut."
            ),
            transit=TransitAccessibility.LIMITED,
            link=av_at_link,
        ),
        _alpine_hike_entry(
            base_route,
            slug="tyrol-grosser-troegler",
            name="Großer Trögler",
            diff_value="T2",
            trail_lon=11.512,
            trail_lat=47.428,
            path=((11.516, 47.432), (11.520, 47.436)),
            elev_min=1580,
            elev_max=2902,
            gain=1322,
            duration=480,
            description=(
                "Karwendel high tour from the Halleranger with well-marked paths "
                "through alpine meadows to a broad rocky summit."
            ),
            transit=TransitAccessibility.LIMITED,
            link=av_at_link,
        ),
        _outdoor_climbing_entry(
            base_route,
            slug="tyrol-elferwand",
            name="Elferwand",
            diff_value="6a",
            diff_scale="French",
            trail_lon=11.318,
            trail_lat=47.112,
            path=((11.320, 47.114), (11.322, 47.116)),
            elev_min=1680,
            elev_max=1880,
            gain=200,
            duration=240,
            description=(
                "Stubai Valley limestone wall above Neustift with long multi-pitch "
                "classics and shorter sport lines on solid grey rock."
            ),
            transit=TransitAccessibility.TRANSIT_FRIENDLY,
            link=av_at_link,
        ),
        _outdoor_climbing_entry(
            base_route,
            slug="tyrol-lixwerk",
            name="Lixwerk",
            diff_value="6b",
            diff_scale="French",
            trail_lon=11.368,
            trail_lat=47.278,
            path=((11.370, 47.280), (11.372, 47.282)),
            elev_min=620,
            elev_max=820,
            gain=200,
            duration=180,
            description=(
                "Innsbruck-area crag on rough limestone above the Inn with quick "
                "access and well-bolted single-pitch routes."
            ),
            transit=TransitAccessibility.TRANSIT_FRIENDLY,
            link=av_at_link,
        ),
        _outdoor_climbing_entry(
            base_route,
            slug="tyrol-schlick-klettergarten",
            name="Schlick Klettergarten",
            diff_value="6a",
            diff_scale="French",
            trail_lon=11.252,
            trail_lat=47.192,
            path=((11.254, 47.194), (11.256, 47.196)),
            elev_min=1320,
            elev_max=1520,
            gain=200,
            duration=210,
            description=(
                "Sunny sectors on the Schlick 2000 plateau with sport and trad "
                "lines on compact dolomitic rock above Fulpmes."
            ),
            transit=TransitAccessibility.TRANSIT_FRIENDLY,
            link=av_at_link,
        ),
        _outdoor_climbing_entry(
            base_route,
            slug="tyrol-karwendel-woerndle",
            name="Wörndle (Karwendel)",
            diff_value="V",
            diff_scale="UIAA",
            trail_lon=11.482,
            trail_lat=47.352,
            path=((11.484, 47.354), (11.486, 47.356)),
            elev_min=1180,
            elev_max=1380,
            gain=200,
            duration=200,
            description=(
                "Karwendel valley crag near the Lafaster Alm with shorter routes on "
                "rough limestone and a forest approach."
            ),
            transit=TransitAccessibility.LIMITED,
            link=av_at_link,
        ),
        _outdoor_climbing_entry(
            base_route,
            slug="tyrol-meiler-platt",
            name="Meiler Platt",
            diff_value="VI-",
            diff_scale="UIAA",
            trail_lon=10.988,
            trail_lat=47.412,
            path=((10.990, 47.414), (10.992, 47.416)),
            elev_min=1780,
            elev_max=1980,
            gain=200,
            duration=360,
            description=(
                "Alpine multi-pitch wall below the Zugspitze massif with long "
                "committing routes and abseil descents on solid Wetterstein limestone."
            ),
            transit=TransitAccessibility.LIMITED,
            link=av_at_link,
        ),
    ]
    assert len(entries) == len(TYROL_CATALOG_SLUGS)
    return entries
