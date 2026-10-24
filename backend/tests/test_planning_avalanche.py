from __future__ import annotations

from datetime import datetime
from datetime import timedelta
from datetime import timezone

from app.data.seed_routes import build_seed_routes
from app.data.seed_routes import seed_route_id
from app.domain.route import Route
from app.planning.avalanche import AvalancheAssessmentKind
from app.planning.avalanche import AvalancheBulletin
from app.planning.avalanche import AvalancheFreshness
from app.planning.avalanche import build_avalanche_planning_input
from app.planning.versions import AVALANCHE_MAX_AGE_SECONDS


def _route_by_slug(slug: str) -> Route:
    route_id = seed_route_id(slug)
    for rid, route in build_seed_routes():
        if rid == route_id:
            return route
    raise AssertionError(f"missing seed route {slug}")


def test_tyrol_and_allgaeu_use_distinct_regional_keys_not_pan_alpine_score() -> None:
    tyrol = _route_by_slug("tyrol-innsbrucker-klettersteig")
    allgaeu = _route_by_slug("allgaeu-mindelheimer-klettersteig")
    now = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    tyrol_input = build_avalanche_planning_input(
        tyrol,
        route_id=seed_route_id("tyrol-innsbrucker-klettersteig"),
        plan_date="2026-07-15",
        now=now,
    )
    allgaeu_input = build_avalanche_planning_input(
        allgaeu,
        route_id=seed_route_id("allgaeu-mindelheimer-klettersteig"),
        plan_date="2026-07-15",
        now=now,
    )
    assert tyrol_input.region_key == "at-tyrol"
    assert allgaeu_input.region_key == "de-allgaeu"
    assert tyrol_input.official_bulletin_url != allgaeu_input.official_bulletin_url
    assert tyrol_input.assessment is AvalancheAssessmentKind.ASSESSED
    assert allgaeu_input.assessment is AvalancheAssessmentKind.ASSESSED


def test_pyrenees_is_not_assessed_with_official_link_only() -> None:
    route = _route_by_slug("unsupported-pyrenees-demo")
    now = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    result = build_avalanche_planning_input(
        route,
        route_id=seed_route_id("unsupported-pyrenees-demo"),
        plan_date="2026-07-15",
        now=now,
    )
    assert result.assessment is AvalancheAssessmentKind.NOT_ASSESSED
    assert result.freshness is AvalancheFreshness.OK
    assert result.official_bulletin_url.startswith("https://")
    assert result.bulletin is None


def test_stale_bulletin_becomes_unknown() -> None:
    route = _route_by_slug("tyrol-innsbrucker-klettersteig")
    now = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    stale_time = now - timedelta(seconds=AVALANCHE_MAX_AGE_SECONDS + 60)
    override = AvalancheBulletin(
        region_key="at-tyrol",
        region_label="Tyrol (Austria)",
        summary="Stale regional bulletin.",
        source_time=stale_time,
        official_bulletin_url="https://example.invalid/at",
    )
    result = build_avalanche_planning_input(
        route,
        route_id=seed_route_id("tyrol-innsbrucker-klettersteig"),
        plan_date="2026-07-15",
        now=now,
        bulletin_override=override,
    )
    assert result.freshness is AvalancheFreshness.STALE
    assert result.assessment is AvalancheAssessmentKind.UNKNOWN


def test_response_payload_has_no_alpine_danger_level_field() -> None:
    from app.planning.avalanche import avalanche_response_payload

    route = _route_by_slug("tyrol-innsbrucker-klettersteig")
    now = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    result = build_avalanche_planning_input(
        route,
        route_id=seed_route_id("tyrol-innsbrucker-klettersteig"),
        plan_date="2026-07-15",
        now=now,
    )
    payload = avalanche_response_payload(result)
    assert payload is not None
    forbidden = {"alpine_danger_level", "danger_level", "eaws_level"}
    assert forbidden.isdisjoint(set(payload.keys()))
