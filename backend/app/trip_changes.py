from __future__ import annotations

from typing import Any


def summarize_plan_run_changes(
    previous: dict[str, Any],
    current: dict[str, Any],
) -> dict[str, Any]:
    changes: list[dict[str, str]] = []
    if previous.get("recommendation") != current.get("recommendation"):
        changes.append(
            {
                "field": "recommendation",
                "from": str(previous.get("recommendation")),
                "to": str(current.get("recommendation")),
            }
        )
    if previous.get("confidence") != current.get("confidence"):
        changes.append(
            {
                "field": "confidence",
                "from": str(previous.get("confidence")),
                "to": str(current.get("confidence")),
            }
        )
    prev_components = previous.get("components") or {}
    curr_components = current.get("components") or {}
    for name in sorted(set(prev_components) | set(curr_components)):
        prev_status = (prev_components.get(name) or {}).get("status")
        curr_status = (curr_components.get(name) or {}).get("status")
        if prev_status != curr_status:
            changes.append(
                {
                    "field": f"components.{name}.status",
                    "from": str(prev_status),
                    "to": str(curr_status),
                }
            )
    return {"changes": changes}
