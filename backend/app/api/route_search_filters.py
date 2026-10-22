from __future__ import annotations

from dataclasses import dataclass

from app.domain.difficulty import _load_mappings
from app.domain.difficulty import canonical_structured_scale
from app.domain.route import RouteType


@dataclass(frozen=True, slots=True)
class DifficultyFilter:
    structured_scale: str
    min_value: str | None
    max_value: str | None


class RouteSearchFilterError(ValueError):
    pass


def parse_difficulty_filter(
    *,
    route_type: RouteType | None,
    difficulty_scale: str | None,
    difficulty_min: str | None,
    difficulty_max: str | None,
) -> DifficultyFilter | None:
    if difficulty_scale is None:
        if difficulty_min is not None or difficulty_max is not None:
            raise RouteSearchFilterError(
                "difficulty_min and difficulty_max require difficulty_scale"
            )
        return None

    canonical = canonical_structured_scale(difficulty_scale.strip())
    if canonical is None:
        raise RouteSearchFilterError("difficulty_scale is not a known structured scale")

    if route_type is not None:
        allowed = _load_mappings()["allowed_scales_by_route_type"].get(route_type.value, [])
        if canonical not in allowed:
            raise RouteSearchFilterError(
                "difficulty_scale is not valid for the requested route_type"
            )

    order: list[str] = _load_mappings()["scales"][canonical]["order"]
    min_value = _normalize_difficulty_bound(difficulty_min, order, "difficulty_min")
    max_value = _normalize_difficulty_bound(difficulty_max, order, "difficulty_max")
    if min_value is not None and max_value is not None:
        if order.index(min_value) > order.index(max_value):
            raise RouteSearchFilterError("difficulty_min cannot be harder than difficulty_max")

    return DifficultyFilter(
        structured_scale=canonical,
        min_value=min_value,
        max_value=max_value,
    )


def difficulty_values_in_filter(difficulty_filter: DifficultyFilter) -> list[str] | None:
    order: list[str] = _load_mappings()["scales"][difficulty_filter.structured_scale]["order"]
    if difficulty_filter.min_value is None and difficulty_filter.max_value is None:
        return None
    start = 0 if difficulty_filter.min_value is None else order.index(difficulty_filter.min_value)
    end = len(order) - 1 if difficulty_filter.max_value is None else order.index(
        difficulty_filter.max_value
    )
    return order[start : end + 1]


def _normalize_difficulty_bound(
    raw: str | None,
    order: list[str],
    field_name: str,
) -> str | None:
    if raw is None:
        return None
    value = raw.strip()
    if not value:
        raise RouteSearchFilterError(f"{field_name} must be non-empty when provided")
    folded = value.casefold()
    for candidate in order:
        if candidate.casefold() == folded:
            return candidate
    raise RouteSearchFilterError(f"{field_name} is not a value on the requested difficulty_scale")
