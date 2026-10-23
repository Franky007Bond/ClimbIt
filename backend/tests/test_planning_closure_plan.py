from datetime import datetime
from datetime import timedelta
from datetime import timezone

from app.domain.closure import ClosureAssessment
from app.domain.closure import ClosureReviewStatus
from app.domain.closure import ClosureStatus
from app.data.seed_routes import PUBLISHED_ALPINE_HIKE_SLUG
from app.data.seed_routes import build_seed_routes
from app.data.seed_routes import seed_route_id
from app.planning.closure_input import build_plan_closure_input

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
