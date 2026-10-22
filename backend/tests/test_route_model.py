from enum import Enum

import pytest
from pydantic import ValidationError

from app.domain.difficulty import map_difficulty
from app.domain.route import (
    Assessment,
    Completeness,
    LineString,
    Point,
    Provenance,
    Publication,
    Region,
    RegionCoverage,
    Route,
    RouteType,
    TransitAccessibility,
)


def _region(**overrides) -> Region:
    payload = {
        "name": "Allgäu",
        "country": "DE",
        "coverage": RegionCoverage.SUPPORTED,
    }
    payload.update(overrides)
    return Region(**payload)


def _point(*, longitude: float = 10.0, latitude: float = 47.0) -> Point:
    return Point(longitude=longitude, latitude=latitude)


def _linestring() -> LineString:
    return LineString(points=[_point(), _point(longitude=10.1, latitude=47.1)])


def _route(**overrides) -> Route:
    payload = {
        "name": "Hindelanger Klettersteig",
        "route_type": RouteType.ALPINE_HIKE,
        "region": _region(),
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
        "season_months": set(),
        "season_note": None,
        "description": "",
        "transit_accessibility": TransitAccessibility.UNKNOWN,
        "official_source_links": [],
        "provenance": Provenance.SEED,
        "completeness": Completeness.INCOMPLETE,
        "assessment": Assessment.UNASSESSED,
    }
    payload.update(overrides)
    return Route(**payload)


def _published_geometry(**overrides) -> dict:
    payload = {
        "publication": Publication.PUBLISHED,
        "trailhead": _point(),
        "linestring": _linestring(),
        "elevation_min_m": 800,
        "elevation_max_m": 1800,
        "duration_minutes": 120,
        "duration_is_estimated": True,
    }
    payload.update(overrides)
    return payload


def _error_text(exc: ValidationError) -> str:
    parts: list[str] = []
    for error in exc.errors():
        loc = ".".join(str(item) for item in error.get("loc", ()))
        parts.append(loc)
        parts.append(error.get("msg", ""))
    return " ".join(parts)


@pytest.mark.parametrize(
    "enum_cls, value",
    [
        (Publication, "quarantined"),
        (Publication, "pending_review"),
        (Publication, "published"),
        (Publication, "unpublished"),
        (Provenance, "seed"),
        (Provenance, "osm"),
        (Provenance, "gpx_upload"),
        (Provenance, "maintainer"),
        (Provenance, "user"),
        (Completeness, "complete"),
        (Completeness, "incomplete"),
        (Assessment, "unassessed"),
        (Assessment, "current"),
        (Assessment, "stale"),
        (RegionCoverage, "supported"),
        (RegionCoverage, "sample"),
        (RegionCoverage, "unsupported"),
        (RouteType, "klettersteig"),
        (RouteType, "alpine_hike"),
        (RouteType, "outdoor_climbing"),
        (TransitAccessibility, "transit_friendly"),
        (TransitAccessibility, "limited"),
        (TransitAccessibility, "unknown"),
    ],
)
def test_enum_values_are_exact_strings(enum_cls: type[Enum], value: str) -> None:
    assert enum_cls(value).value == value


@pytest.mark.parametrize(
    "enum_cls, bad",
    [
        (Publication, "draft"),
        (Provenance, "import"),
        (Completeness, "partial"),
        (Assessment, "fresh"),
        (RegionCoverage, "full"),
        (RouteType, "via_ferrata"),
        (TransitAccessibility, "good"),
    ],
)
def test_unknown_enum_string_raises(enum_cls: type[Enum], bad: str) -> None:
    with pytest.raises((ValidationError, ValueError)):
        enum_cls(bad)


def test_region_fields_and_route_has_no_coverage() -> None:
    region = _region(name="  Tyrol  ", country="AT", coverage=RegionCoverage.SAMPLE)
    assert region.name == "Tyrol"
    assert region.country == "AT"
    assert region.coverage is RegionCoverage.SAMPLE
    assert "coverage" not in Route.model_fields
    assert "coverage" not in Route.model_json_schema().get("properties", {})
    route = _route(region=region)
    assert route.region.coverage is RegionCoverage.SAMPLE
    with pytest.raises(ValidationError):
        Route(**{**_route().model_dump(), "coverage": "supported"})


def test_extra_fields_are_forbidden() -> None:
    with pytest.raises(ValidationError):
        _route(safety_buffer=30)
    with pytest.raises(ValidationError):
        Region(name="Allgäu", country="DE", coverage=RegionCoverage.SUPPORTED, extra="no")


def test_published_alpine_hike_without_component_minutes() -> None:
    route = _route(
        route_type=RouteType.ALPINE_HIKE,
        **_published_geometry(),
        approach_minutes=None,
        technical_minutes=None,
        descent_minutes=None,
    )
    assert route.publication is Publication.PUBLISHED
    assert route.approach_minutes is None


def test_published_outdoor_climbing_without_component_minutes() -> None:
    route = _route(
        route_type=RouteType.OUTDOOR_CLIMBING,
        **_published_geometry(),
        approach_minutes=None,
        technical_minutes=None,
        descent_minutes=None,
    )
    assert route.route_type is RouteType.OUTDOOR_CLIMBING


def test_published_klettersteig_with_component_minutes() -> None:
    route = _route(
        route_type=RouteType.KLETTERSTEIG,
        **_published_geometry(
            duration_minutes=180,
        ),
        approach_minutes=40,
        technical_minutes=90,
        descent_minutes=50,
    )
    assert route.publication is Publication.PUBLISHED
    assert route.duration_minutes == 180


@pytest.mark.parametrize(
    "missing_field",
    [
        "trailhead",
        "linestring",
        "elevation_min_m",
        "elevation_max_m",
        "duration_minutes",
    ],
)
def test_published_alpine_hike_requires_each_published_field(missing_field: str) -> None:
    payload = _published_geometry()
    payload[missing_field] = None
    with pytest.raises(ValidationError) as exc_info:
        _route(route_type=RouteType.ALPINE_HIKE, **payload)
    assert missing_field in _error_text(exc_info.value)


def test_trailhead_and_linestring_none_allowed_when_not_published() -> None:
    route = _route(
        publication=Publication.QUARANTINED,
        trailhead=None,
        linestring=None,
    )
    assert route.trailhead is None
    assert route.linestring is None


def test_empty_or_single_point_linestring_invalid_even_when_quarantined() -> None:
    with pytest.raises(ValidationError):
        _route(publication=Publication.QUARANTINED, linestring=[])
    with pytest.raises(ValidationError):
        _route(publication=Publication.QUARANTINED, linestring=[_point()])


def test_point_bounds() -> None:
    Point(longitude=-180, latitude=-90)
    Point(longitude=180, latitude=90)
    with pytest.raises(ValidationError):
        Point(longitude=-180.1, latitude=0)
    with pytest.raises(ValidationError):
        Point(longitude=0, latitude=90.1)


def test_elevation_order_and_negative_meters() -> None:
    _route(
        publication=Publication.QUARANTINED,
        elevation_min_m=-12,
        elevation_max_m=-12,
    )
    with pytest.raises(ValidationError):
        _route(
            publication=Publication.QUARANTINED,
            elevation_min_m=100,
            elevation_max_m=99,
        )


@pytest.mark.parametrize("field", ["elevation_gain_m", "elevation_loss_m"])
def test_negative_gain_or_loss_invalid(field: str) -> None:
    with pytest.raises(ValidationError):
        _route(**{field: -1})


@pytest.mark.parametrize(
    "field",
    ["duration_minutes", "approach_minutes", "technical_minutes", "descent_minutes"],
)
@pytest.mark.parametrize("value", [0, -1])
def test_non_positive_minutes_invalid(field: str, value: int) -> None:
    with pytest.raises(ValidationError):
        _route(publication=Publication.QUARANTINED, **{field: value})


@pytest.mark.parametrize(
    "publication",
    [Publication.PENDING_REVIEW, Publication.PUBLISHED, Publication.UNPUBLISHED],
)
@pytest.mark.parametrize(
    "missing",
    ["approach_minutes", "technical_minutes", "descent_minutes"],
)
def test_klettersteig_cannot_leave_quarantine_without_components(
    publication: Publication, missing: str
) -> None:
    payload = {
        "route_type": RouteType.KLETTERSTEIG,
        "publication": publication,
        "approach_minutes": 10,
        "technical_minutes": 20,
        "descent_minutes": 30,
        "duration_minutes": 60,
        "duration_is_estimated": True,
    }
    if publication is Publication.PUBLISHED:
        payload.update(_published_geometry(duration_minutes=60))
        payload["approach_minutes"] = 10
        payload["technical_minutes"] = 20
        payload["descent_minutes"] = 30
    payload[missing] = None
    with pytest.raises(ValidationError) as exc_info:
        _route(**payload)
    assert missing in _error_text(exc_info.value)


def test_quarantined_klettersteig_may_omit_geometry_and_components() -> None:
    route = _route(
        route_type=RouteType.KLETTERSTEIG,
        publication=Publication.QUARANTINED,
        trailhead=None,
        linestring=None,
        elevation_min_m=None,
        elevation_max_m=None,
        approach_minutes=None,
        technical_minutes=None,
        descent_minutes=None,
    )
    assert route.publication is Publication.QUARANTINED


def test_alpine_hike_pending_review_without_components() -> None:
    route = _route(
        route_type=RouteType.ALPINE_HIKE,
        publication=Publication.PENDING_REVIEW,
        approach_minutes=None,
        technical_minutes=None,
        descent_minutes=None,
    )
    assert route.publication is Publication.PENDING_REVIEW


def test_duration_must_equal_sum_of_components_when_all_set() -> None:
    with pytest.raises(ValidationError):
        _route(
            publication=Publication.QUARANTINED,
            duration_minutes=100,
            approach_minutes=10,
            technical_minutes=20,
            descent_minutes=30,
        )
    route = _route(
        publication=Publication.QUARANTINED,
        duration_minutes=60,
        approach_minutes=10,
        technical_minutes=20,
        descent_minutes=30,
        duration_is_estimated=True,
    )
    assert route.duration_is_estimated is True


def test_original_difficulty_stored_not_mapped() -> None:
    for value, scale in (("Z", "Huebler"), ("T7", "SAC"), ("5.14a", "YDS")):
        route = _route(
            original_difficulty_value=value,
            original_difficulty_scale=scale,
        )
        assert route.original_difficulty_value == value
        assert route.original_difficulty_scale == scale
    field_names = set(Route.model_fields)
    assert "normalized_grade" not in field_names
    assert "mapped_grade" not in field_names
    assert "mapping_confidence" not in field_names
    both_none = _route(
        publication=Publication.QUARANTINED,
        original_difficulty_value=None,
        original_difficulty_scale=None,
    )
    assert both_none.original_difficulty_value is None
    with pytest.raises(ValidationError):
        _route(original_difficulty_value="Z", original_difficulty_scale=None)
    with pytest.raises(ValidationError):
        _route(original_difficulty_value=None, original_difficulty_scale="Huebler")


def test_route_type_must_be_enum_and_name_must_be_non_empty() -> None:
    with pytest.raises(ValidationError):
        Route.model_validate({**_route().model_dump(mode="json"), "route_type": "hike"})
    with pytest.raises(ValidationError):
        _route(name="")
    with pytest.raises(ValidationError):
        _route(name="   ")


def test_season_months_and_official_source_links() -> None:
    with pytest.raises(ValidationError):
        _route(season_months={0})
    with pytest.raises(ValidationError):
        _route(season_months={13})
    route = Route.model_validate(
        {**_route().model_dump(mode="json"), "season_months": [6, 6, 7]}
    )
    assert route.season_months == {6, 7}
    with pytest.raises(ValidationError):
        _route(official_source_links=["ftp://example.invalid/x"])
    with pytest.raises(ValidationError):
        _route(official_source_links=["not-a-url"])
    stored = _route(official_source_links=["https://example.invalid/source"])
    assert stored.official_source_links == ["https://example.invalid/source"]


def test_gpx_empty_string_invalid_none_and_text_ok() -> None:
    with pytest.raises(ValidationError):
        _route(gpx="")
    assert _route(gpx=None).gpx is None
    raw = "<gpx>not parsed here</gpx>"
    assert _route(gpx=raw).gpx == raw


def test_duration_is_estimated_cannot_be_omitted() -> None:
    payload = _route().model_dump()
    del payload["duration_is_estimated"]
    with pytest.raises(ValidationError):
        Route.model_validate(payload)


def test_route_omits_out_of_scope_fields() -> None:
    fields = set(Route.model_fields)
    for unexpected in (
        "coverage",
        "safety_buffer",
        "id",
        "normalized_grade",
        "mapped_grade",
        "mapping_confidence",
        "closure_assessment",
        "reviewed_at",
        "expires_at",
        "revisions",
    ):
        assert unexpected not in fields


def test_attached_difficulty_keeps_originals() -> None:
    mapped = map_difficulty(RouteType.KLETTERSTEIG, "K3", "k1_k6")
    route = _route(
        route_type=RouteType.KLETTERSTEIG,
        original_difficulty_value="K3",
        original_difficulty_scale="k1_k6",
        difficulty=mapped,
    )
    assert route.original_difficulty_value == "K3"
    assert route.original_difficulty_scale == "k1_k6"
    assert route.difficulty is not None
    assert route.difficulty.mapped_huebler == "C"
    assert route.difficulty.original_value == "K3"
    assert route.difficulty.route_type is RouteType.KLETTERSTEIG
    with pytest.raises(ValidationError):
        _route(mapped_grade="C")
    for name in ("rank", "numeric", "numeric_value", "comparable_rank"):
        assert name not in Route.model_fields
        assert name not in route.model_dump()


def test_route_difficulty_defaults_to_none() -> None:
    route = _route()
    assert route.difficulty is None


def test_difficulty_must_match_route_originals_and_type() -> None:
    mapped = map_difficulty(RouteType.KLETTERSTEIG, "C", "huebler")
    with pytest.raises(ValidationError):
        _route(
            route_type=RouteType.ALPINE_HIKE,
            original_difficulty_value="C",
            original_difficulty_scale="huebler",
            difficulty=mapped,
        )
    with pytest.raises(ValidationError):
        _route(
            route_type=RouteType.KLETTERSTEIG,
            original_difficulty_value="D",
            original_difficulty_scale="huebler",
            difficulty=mapped,
        )
    with pytest.raises(ValidationError):
        _route(
            route_type=RouteType.KLETTERSTEIG,
            original_difficulty_value="C",
            original_difficulty_scale="Huebler",
            difficulty=mapped,
        )


def test_mapped_difficulty_rejected_when_originals_are_none() -> None:
    mapped = map_difficulty(RouteType.KLETTERSTEIG, "C", "huebler")
    mismatched = mapped.model_copy(
        update={"original_value": None, "original_scale": None}
    )
    with pytest.raises(ValidationError):
        _route(
            publication=Publication.QUARANTINED,
            original_difficulty_value=None,
            original_difficulty_scale=None,
            difficulty=mismatched,
        )


def test_unmapped_difficulty_may_attach_when_originals_are_none() -> None:
    route = _route(
        publication=Publication.QUARANTINED,
        original_difficulty_value=None,
        original_difficulty_scale=None,
        difficulty=map_difficulty(RouteType.ALPINE_HIKE, None, None),
    )
    assert route.difficulty is not None
    assert route.difficulty.mapping_confidence.value == "unmapped"


def test_opaque_originals_still_construct_without_mapping() -> None:
    route = _route(
        original_difficulty_value="Z",
        original_difficulty_scale="Huebler",
        difficulty=None,
    )
    assert route.original_difficulty_value == "Z"
    assert route.difficulty is None
