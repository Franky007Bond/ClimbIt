from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.planning.versions import MOCK_TRANSIT_ADAPTER_VERSION


class ComponentStatus(StrEnum):
    OK = "ok"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class TransitSummary:
    status: ComponentStatus
    adapter_version: str
    summary: str
    origin_region: str | None
    last_return_feasible: bool | None


def mock_transit_summary(origin: str) -> TransitSummary:
    region = _coarse_origin_region(origin)
    degraded = origin.strip().lower() in {"", "unknown", "n/a"}
    status = ComponentStatus.DEGRADED if degraded else ComponentStatus.OK
    return TransitSummary(
        status=status,
        adapter_version=MOCK_TRANSIT_ADAPTER_VERSION,
        summary="Mock outbound connection to trailhead access point.",
        origin_region=region,
        last_return_feasible=True if not degraded else None,
    )


def _coarse_origin_region(origin: str) -> str | None:
    cleaned = origin.strip()
    if not cleaned:
        return None
    # Coarse region only — never persist the exact origin string.
    if "munich" in cleaned.lower():
        return "DE-BY"
    if "geneva" in cleaned.lower() or "genève" in cleaned.lower():
        return "CH-GE"
    if "chamonix" in cleaned.lower():
        return "FR-74"
    return "region-unknown"
