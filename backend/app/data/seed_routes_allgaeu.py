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

ALLGAEU_LAUNCH_PUBLISHED_COUNT = 20

ALLGAEU_CATALOG_SLUGS: tuple[str, ...] = (
    "allgaeu-mindelheimer-klettersteig",
    "allgaeu-allgaeuer-klettersteig",
    "allgaeu-dietersbacher-steig",
    "allgaeu-walsersteig",
    "allgaeu-tannheimer-klettersteig",
    "allgaeu-heilbronnweg",
    "allgaeu-hochvogel",
    "allgaeu-grosser-krottenkopf",
    "allgaeu-maedelegabel",
    "allgaeu-rubihorn",
    "allgaeu-schrecksee",
    "allgaeu-hoellental",
    "allgaeu-blaustein-kolbenstein",
    "allgaeu-emporer",
    "allgaeu-falkenstein",
    "allgaeu-breitenberg-klettergarten",
    "allgaeu-graenertobel",
    "allgaeu-alpspitz-westwand",
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
    from app.data.seed_routes import ALLGAEU
    from app.data.seed_routes import seed_route_id

    trailhead, linestring = _trail_line(trail_lon, trail_lat, *path)
    difficulty = map_difficulty(RouteType.KLETTERSTEIG, diff_value, diff_scale)
    route = base_route(
        name=name,
        route_type=RouteType.KLETTERSTEIG,
        region=ALLGAEU,
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
    from app.data.seed_routes import ALLGAEU
    from app.data.seed_routes import seed_route_id

    trailhead, linestring = _trail_line(trail_lon, trail_lat, *path)
    difficulty = map_difficulty(RouteType.ALPINE_HIKE, diff_value, "SAC")
    route = base_route(
        name=name,
        route_type=RouteType.ALPINE_HIKE,
        region=ALLGAEU,
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
    from app.data.seed_routes import ALLGAEU
    from app.data.seed_routes import seed_route_id

    trailhead, linestring = _trail_line(trail_lon, trail_lat, *path)
    difficulty = map_difficulty(RouteType.OUTDOOR_CLIMBING, diff_value, diff_scale)
    route = base_route(
        name=name,
        route_type=RouteType.OUTDOOR_CLIMBING,
        region=ALLGAEU,
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


def build_allgaeu_catalog_routes(
    base_route: Callable[..., Route],
) -> list[tuple[uuid.UUID, Route]]:
    av_link = "https://www.alpenverein.de/"
    entries: list[tuple[uuid.UUID, Route]] = [
        _klettersteig_entry(
            base_route,
            slug="allgaeu-mindelheimer-klettersteig",
            name="Mindelheimer Klettersteig",
            diff_value="K4",
            diff_scale="k1_k6",
            trail_lon=10.412,
            trail_lat=47.421,
            path=((10.418, 47.428), (10.425, 47.435)),
            elev_min=1450,
            elev_max=2220,
            gain=770,
            duration=360,
            approach=90,
            technical=180,
            descent=90,
            description=(
                "Classic west-to-east traverse on the Heubachgrat with long exposed "
                "sections; typical Mindelheim hut approach from the Rappensee side."
            ),
            transit=TransitAccessibility.LIMITED,
            link=av_link,
        ),
        _klettersteig_entry(
            base_route,
            slug="allgaeu-allgaeuer-klettersteig",
            name="Allgäuer Klettersteig",
            diff_value="K3",
            diff_scale="k1_k6",
            trail_lon=10.348,
            trail_lat=47.462,
            path=((10.352, 47.468), (10.358, 47.474)),
            elev_min=1180,
            elev_max=1840,
            gain=660,
            duration=300,
            approach=75,
            technical=150,
            descent=75,
            description=(
                "Short but steep iron path on the east flank above Bad Hindelang; "
                "often combined with a ridge walk toward the Hintersteiner See."
            ),
            transit=TransitAccessibility.TRANSIT_FRIENDLY,
            link=av_link,
        ),
        _klettersteig_entry(
            base_route,
            slug="allgaeu-dietersbacher-steig",
            name="Dietersbacher Steig",
            diff_value="K3",
            diff_scale="k1_k6",
            trail_lon=10.285,
            trail_lat=47.518,
            path=((10.290, 47.522), (10.296, 47.526)),
            elev_min=920,
            elev_max=1680,
            gain=760,
            duration=330,
            approach=80,
            technical=170,
            descent=80,
            description=(
                "Sunny south-facing klettersteig above Oberstdorf with views toward "
                "the Kleinwalsertal; cables and rungs on compact limestone."
            ),
            transit=TransitAccessibility.TRANSIT_FRIENDLY,
            link=av_link,
        ),
        _klettersteig_entry(
            base_route,
            slug="allgaeu-walsersteig",
            name="Walsersteig",
            diff_value="K2",
            diff_scale="k1_k6",
            trail_lon=10.252,
            trail_lat=47.502,
            path=((10.256, 47.506), (10.261, 47.510)),
            elev_min=860,
            elev_max=1520,
            gain=660,
            duration=270,
            approach=70,
            technical=130,
            descent=70,
            description=(
                "Family-friendly secured path on the Ifen massif above the Kleinwalsertal "
                "with short technical steps and wide ledges."
            ),
            transit=TransitAccessibility.LIMITED,
            link=av_link,
        ),
        _klettersteig_entry(
            base_route,
            slug="allgaeu-tannheimer-klettersteig",
            name="Tannheimer Klettersteig",
            diff_value="K3",
            diff_scale="k1_k6",
            trail_lon=10.528,
            trail_lat=47.468,
            path=((10.532, 47.472), (10.538, 47.476)),
            elev_min=1120,
            elev_max=1960,
            gain=840,
            duration=390,
            approach=100,
            technical=190,
            descent=100,
            description=(
                "Tyrol-border route on the Gimpel–Kreuzspitze chain; long ridge "
                "exposure with several re-ascents along the crest."
            ),
            transit=TransitAccessibility.LIMITED,
            link=av_link,
        ),
        _alpine_hike_entry(
            base_route,
            slug="allgaeu-heilbronnweg",
            name="Heilbronnweg",
            diff_value="T4",
            trail_lon=10.398,
            trail_lat=47.505,
            path=((10.404, 47.510), (10.410, 47.515)),
            elev_min=1220,
            elev_max=2220,
            gain=1000,
            duration=480,
            description=(
                "Exposed alpine path from the Rappensee area to the Heilbronner Weg "
                "on the main Allgäu crest; sure-footedness and a head for heights required."
            ),
            transit=TransitAccessibility.LIMITED,
            link=av_link,
        ),
        _alpine_hike_entry(
            base_route,
            slug="allgaeu-hochvogel",
            name="Hochvogel",
            diff_value="T3",
            trail_lon=10.318,
            trail_lat=47.488,
            path=((10.322, 47.492), (10.326, 47.496)),
            elev_min=1280,
            elev_max=2592,
            gain=1310,
            duration=540,
            description=(
                "Normal route from the Prinz-Luitpold-Haus across scree and blocky "
                "terrain to the Hochvogel summit on the Austrian–German border."
            ),
            transit=TransitAccessibility.LIMITED,
            link=av_link,
        ),
        _alpine_hike_entry(
            base_route,
            slug="allgaeu-grosser-krottenkopf",
            name="Großer Krottenkopf",
            diff_value="T3",
            trail_lon=10.442,
            trail_lat=47.408,
            path=((10.446, 47.412), (10.450, 47.416)),
            elev_min=1420,
            elev_max=2656,
            gain=1230,
            duration=510,
            description=(
                "Highest peak in the Allgäu Alps via the Mindelheimer or Rappensee "
                "approaches; long day with glacier-free but alpine terrain."
            ),
            transit=TransitAccessibility.LIMITED,
            link=av_link,
        ),
        _alpine_hike_entry(
            base_route,
            slug="allgaeu-maedelegabel",
            name="Mädelegabel",
            diff_value="T3",
            trail_lon=10.362,
            trail_lat=47.478,
            path=((10.366, 47.482), (10.370, 47.486)),
            elev_min=1180,
            elev_max=2424,
            gain=1240,
            duration=480,
            description=(
                "Classic summit on the main chain between the Hornbachkette and "
                "Hochvogel; steep grass and rock steps near the top."
            ),
            transit=TransitAccessibility.LIMITED,
            link=av_link,
        ),
        _alpine_hike_entry(
            base_route,
            slug="allgaeu-rubihorn",
            name="Rubihorn",
            diff_value="T2",
            trail_lon=10.278,
            trail_lat=47.532,
            path=((10.282, 47.536), (10.286, 47.540)),
            elev_min=820,
            elev_max=1952,
            gain=1130,
            duration=360,
            description=(
                "Popular Oberstdorf summit with a well-marked path through alpine "
                "meadows and a rocky final cone overlooking the Stillach valley."
            ),
            transit=TransitAccessibility.TRANSIT_FRIENDLY,
            link=av_link,
        ),
        _alpine_hike_entry(
            base_route,
            slug="allgaeu-schrecksee",
            name="Schrecksee",
            diff_value="T3",
            trail_lon=10.304,
            trail_lat=47.496,
            path=((10.308, 47.500), (10.312, 47.504)),
            elev_min=1080,
            elev_max=1813,
            gain=730,
            duration=420,
            description=(
                "Turquoise alpine lake beneath the Hochvogel north face; steep "
                "switchbacks from the Unterjoch trailhead with high scenic payoff."
            ),
            transit=TransitAccessibility.TRANSIT_FRIENDLY,
            link=av_link,
        ),
        _alpine_hike_entry(
            base_route,
            slug="allgaeu-hoellental",
            name="Höllental",
            diff_value="T4",
            trail_lon=10.392,
            trail_lat=47.512,
            path=((10.396, 47.516), (10.400, 47.520)),
            elev_min=1240,
            elev_max=2140,
            gain=900,
            duration=450,
            description=(
                "Deep gorge and crest walk above Hinterstein with cables on the "
                "steeper steps; often done as a loop with the Hintersteiner See."
            ),
            transit=TransitAccessibility.TRANSIT_FRIENDLY,
            link=av_link,
        ),
        _outdoor_climbing_entry(
            base_route,
            slug="allgaeu-blaustein-kolbenstein",
            name="Kolbenstein (Blaustein)",
            diff_value="6b",
            diff_scale="French",
            trail_lon=10.448,
            trail_lat=47.508,
            path=((10.450, 47.510), (10.452, 47.512)),
            elev_min=980,
            elev_max=1180,
            gain=200,
            duration=240,
            description=(
                "Compact limestone crag above Hinterstein with multi-pitch classics "
                "on solid grey rock; approach from the valley parking."
            ),
            transit=TransitAccessibility.TRANSIT_FRIENDLY,
            link=av_link,
        ),
        _outdoor_climbing_entry(
            base_route,
            slug="allgaeu-falkenstein",
            name="Falkenstein",
            diff_value="5c",
            diff_scale="French",
            trail_lon=10.334,
            trail_lat=47.456,
            path=((10.336, 47.458), (10.338, 47.460)),
            elev_min=1020,
            elev_max=1220,
            gain=200,
            duration=210,
            description=(
                "Sunny south-west facing walls near Bad Hindelang with single- and "
                "multi-pitch routes on rough limestone."
            ),
            transit=TransitAccessibility.TRANSIT_FRIENDLY,
            link=av_link,
        ),
        _outdoor_climbing_entry(
            base_route,
            slug="allgaeu-breitenberg-klettergarten",
            name="Breitenberg Klettergarten",
            diff_value="6b",
            diff_scale="French",
            trail_lon=10.218,
            trail_lat=47.528,
            path=((10.220, 47.530), (10.222, 47.532)),
            elev_min=780,
            elev_max=980,
            gain=200,
            duration=180,
            description=(
                "Valley-side sport and trad sectors on the Breitenberg above "
                "Oberjoch with quick access and long season."
            ),
            transit=TransitAccessibility.TRANSIT_FRIENDLY,
            link=av_link,
        ),
        _outdoor_climbing_entry(
            base_route,
            slug="allgaeu-graenertobel",
            name="Gränertobel",
            diff_value="V",
            diff_scale="UIAA",
            trail_lon=10.296,
            trail_lat=47.424,
            path=((10.298, 47.426), (10.300, 47.428)),
            elev_min=940,
            elev_max=1140,
            gain=200,
            duration=200,
            description=(
                "Shaded gorge crag near Blaichach with shorter routes on pocketed "
                "limestone; popular on hot summer days."
            ),
            transit=TransitAccessibility.LIMITED,
            link=av_link,
        ),
        _outdoor_climbing_entry(
            base_route,
            slug="allgaeu-alpspitz-westwand",
            name="Alpspitz Westwand",
            diff_value="VII-",
            diff_scale="UIAA",
            trail_lon=10.312,
            trail_lat=47.514,
            path=((10.314, 47.516), (10.316, 47.518)),
            elev_min=1100,
            elev_max=1300,
            gain=200,
            duration=360,
            description=(
                "Alpine multi-pitch wall above the Stillach valley; long routes "
                "with commitment and descent via abseil chains."
            ),
            transit=TransitAccessibility.LIMITED,
            link=av_link,
        ),
        _outdoor_climbing_entry(
            base_route,
            slug="allgaeu-emporer",
            name="Emporer",
            diff_value="6c",
            diff_scale="French",
            trail_lon=10.326,
            trail_lat=47.508,
            path=((10.328, 47.510), (10.330, 47.512)),
            elev_min=1050,
            elev_max=1250,
            gain=200,
            duration=240,
            description=(
                "Steep pocketed limestone above the Stillach with well-bolted "
                "single-pitch lines and a short forest approach."
            ),
            transit=TransitAccessibility.LIMITED,
            link=av_link,
        ),
    ]
    assert len(entries) == len(ALLGAEU_CATALOG_SLUGS)
    return entries
