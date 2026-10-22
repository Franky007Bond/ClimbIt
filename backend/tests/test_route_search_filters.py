import pytest

from app.api.route_search_filters import RouteSearchFilterError
from app.api.route_search_filters import parse_difficulty_filter
from app.domain.route import RouteType


def test_difficulty_bounds_require_scale() -> None:
    with pytest.raises(RouteSearchFilterError, match="difficulty_scale"):
        parse_difficulty_filter(
            route_type=None,
            difficulty_scale=None,
            difficulty_min="K3",
            difficulty_max=None,
        )


def test_klettersteig_scale_rejected_for_alpine_hike_route_type() -> None:
    with pytest.raises(RouteSearchFilterError, match="route_type"):
        parse_difficulty_filter(
            route_type=RouteType.ALPINE_HIKE,
            difficulty_scale="k1_k6",
            difficulty_min="K3",
            difficulty_max=None,
        )


def test_unknown_difficulty_scale_raises() -> None:
    with pytest.raises(RouteSearchFilterError, match="difficulty_scale"):
        parse_difficulty_filter(
            route_type=RouteType.KLETTERSTEIG,
            difficulty_scale="not_a_real_scale",
            difficulty_min=None,
            difficulty_max=None,
        )


def test_difficulty_min_harder_than_max_raises() -> None:
    with pytest.raises(RouteSearchFilterError, match="difficulty_min"):
        parse_difficulty_filter(
            route_type=RouteType.KLETTERSTEIG,
            difficulty_scale="k1_k6",
            difficulty_min="K5",
            difficulty_max="K2",
        )
