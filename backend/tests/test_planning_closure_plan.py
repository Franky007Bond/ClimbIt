from datetime import datetime
from datetime import timedelta
from datetime import timezone

from app.domain.closure import ClosureAssessment
from app.domain.closure import ClosureReviewStatus
from app.domain.closure import ClosureStatus
from app.data.seed_routes import PUBLISHED_ALPINE_HIKE_SLUG
from app.data.seed_routes import build_seed_routes
from app.data.seed_routes import seed_route_id
from app.planning.avalanche import AvalancheAssessmentKind
from app.planning.avalanche import AvalancheFreshness
from app.planning.avalanche import AvalanchePlanningInput
from app.planning.closure_input import build_plan_closure_input
from app.planning.recommendation import Recommendation
from app.planning.recommendation import judge_recommendation
from app.planning.thunderstorm import assess_thunderstorm_risk
from app.planning.weather import WeatherAssessment
from app.planning.weather import WeatherFreshness
from app.planning.weather import WeatherForecast

UTC = timezone.utc


def _published_route(**overrides: object):
    target_id = seed_route_id(PUBLISHED_ALPINE_HIKE_SLUG)
    route = next(r for route_id, r in build_seed_routes() if route_id == target_id)
    return route.model_copy(update=overrides)


def _closure(**overrides: object) -> ClosureAssessment:
    now = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
    payload: dict[str, object] = {
        "status": ClosureStatus.ACTIVE,
        "source_url": "https://example.com/closure",
        "owner": "operator",
        "review_status": ClosureReviewStatus.REVIEWED,
        "created_at": now,
        "updated_at": now,
        "reviewed_at": now,
        "expires_at": now + timedelta(days=30),
    }
    payload.update(overrides)
    return ClosureAssessment(**payload)  # type: ignore[arg-type]


def test_active_closure_is_hard_blocker() -> None:
    now = datetime(2026, 7, 15, 8, 0, tzinfo=UTC)
    route = _published_route(closure_assessment=_closure(status=ClosureStatus.ACTIVE))
    result = build_plan_closure_input(route, now)
    assert result.planning_value == "active"
    assert result.hard_blocker is True


def test_missing_closure_is_unknown_not_none_known() -> None:
    now = datetime(2026, 7, 15, 8, 0, tzinfo=UTC)
    route = _published_route(closure_assessment=None)
    result = build_plan_closure_input(route, now)
    assert result.planning_value == "unknown"


def test_expired_closure_shows_effective_status_but_unknown_to_planning() -> None:
    reviewed = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
    expires = datetime(2026, 7, 10, 0, 0, tzinfo=UTC)
    after_expiry = datetime(2026, 7, 11, 8, 0, tzinfo=UTC)
    route = _published_route(
        closure_assessment=_closure(
            status=ClosureStatus.NONE_KNOWN,
            created_at=reviewed,
            updated_at=reviewed,
            reviewed_at=reviewed,
            expires_at=expires,
        )
    )
    result = build_plan_closure_input(route, after_expiry)
    assert result.effective_status == "expired"
    assert result.planning_value == "unknown"
    assert result.hard_blocker is False
    assert route.closure_assessment is not None
    assert route.closure_assessment.status is ClosureStatus.NONE_KNOWN


def _ideal_weather() -> WeatherAssessment:
    forecast = WeatherForecast(
        temperature_c=10,
        wind_ms=2,
        precipitation_mm=0,
        freezing_level_m=3000,
        cape_j_kg=50,
        precip_probability=5,
        source_time=datetime(2026, 7, 1, 12, 0, tzinfo=UTC),
    )
    return WeatherAssessment(
        freshness=WeatherFreshness.OK,
        forecast=forecast,
        adapter_version="mock",
    )


def _ideal_avalanche() -> AvalanchePlanningInput:
    return AvalanchePlanningInput(
        freshness=AvalancheFreshness.OK,
        assessment=AvalancheAssessmentKind.NOT_ASSESSED,
        region_key="fr-chamonix",
        region_label="Chamonix",
        official_bulletin_url="https://example.invalid/fr",
        bulletin=None,
        adapter_version="mock",
    )


def test_expired_closure_turns_green_inputs_into_critical_gap() -> None:
    reviewed = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
    expires = datetime(2026, 7, 10, 0, 0, tzinfo=UTC)
    before = datetime(2026, 7, 9, 8, 0, tzinfo=UTC)
    after = datetime(2026, 7, 11, 8, 0, tzinfo=UTC)
    route = _published_route(
        closure_assessment=_closure(
            status=ClosureStatus.NONE_KNOWN,
            created_at=reviewed,
            updated_at=reviewed,
            reviewed_at=reviewed,
            expires_at=expires,
        )
    )
    weather = _ideal_weather()
    avalanche = _ideal_avalanche()
    thunder = assess_thunderstorm_risk(
        weather.forecast, exposure="moderate", start_hour_local=8
    )

    before_closure = build_plan_closure_input(route, before)
    after_closure = build_plan_closure_input(route, after)
    assert before_closure.planning_value == "none_known"
    assert after_closure.planning_value == "unknown"

    before_rec = judge_recommendation(
        route,
        weather=weather,
        avalanche=avalanche,
        closure=before_closure,
        thunderstorm=thunder,
        daylight_calculable=True,
    )
    after_rec = judge_recommendation(
        route,
        weather=weather,
        avalanche=avalanche,
        closure=after_closure,
        thunderstorm=thunder,
        daylight_calculable=True,
    )
    assert before_rec.recommendation is Recommendation.GREEN
    assert after_rec.recommendation is not Recommendation.GREEN
    assert "closure_unknown" in after_rec.critical_gaps
