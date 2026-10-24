"""Non-production injection hook for plan-failure observability drills."""

from __future__ import annotations

import os

_TRUTHY = frozenset({"1", "true", "yes", "on"})


def plan_failure_drill_enabled() -> bool:
    """Return True when a drill should force trip-plan requests to fail."""
    raw = os.environ.get("CLIMBIT_PLAN_FAILURE_DRILL", "").strip().lower()
    if raw not in _TRUTHY:
        return False
    environment = os.environ.get("CLIMBIT_ENVIRONMENT", "local").strip().lower()
    return environment != "production"


def plan_failure_drill_detail() -> str:
    return "Planning temporarily unavailable (failure drill)"
