from __future__ import annotations

from typing import Any


def sanitized_shared_snapshot(
    *,
    plan_run_id: str,
    route_id: str,
    input_snapshot: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    return {
        "plan_run_id": plan_run_id,
        "route_id": route_id,
        "plan_date": str(input_snapshot.get("plan_date", "")),
        "recommendation": str(result.get("recommendation", "unknown")),
        "confidence": str(result.get("confidence", "unknown")),
        "components": dict(result.get("components") or {}),
        "explanation": list(result.get("explanation") or []),
        "origin_region": result.get("origin_region"),
    }
