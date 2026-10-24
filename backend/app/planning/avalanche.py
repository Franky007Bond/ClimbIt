from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Any
from typing import Protocol
from uuid import UUID

from app.domain.route import Route
from app.planning.versions import AVALANCHE_MAX_AGE_SECONDS
from app.planning.versions import MOCK_AVALANCHE_ADAPTER_VERSION

_REGISTRY_PATH = Path(__file__).resolve().parent.parent / "data" / "avalanche_regions.json"


class AvalancheFreshness(StrEnum):
    OK = "ok"
    STALE = "stale"
    UNKNOWN = "unknown"


class AvalancheAssessmentKind(StrEnum):
    ASSESSED = "assessed"
    NOT_ASSESSED = "not_assessed"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class AvalancheRegionConfig:
    region_key: str
    region_label: str
    adapter_id: str | None
    official_bulletin_url: str
    permitted_feed: bool


@dataclass(frozen=True, slots=True)
class AvalancheBulletin:
    region_key: str
    region_label: str
    summary: str
    source_time: datetime
    max_age_seconds: int = AVALANCHE_MAX_AGE_SECONDS
    official_bulletin_url: str = ""


@dataclass(frozen=True, slots=True)
class AvalanchePlanningInput:
    freshness: AvalancheFreshness
    assessment: AvalancheAssessmentKind
    region_key: str
    region_label: str
    official_bulletin_url: str
    bulletin: AvalancheBulletin | None
    adapter_version: str


class AvalanchePort(Protocol):
    adapter_version: str

    def fetch_bulletin(
        self,
        *,
        route_id: UUID,
        region_key: str,
        adapter_id: str,
        plan_date: str,
    ) -> AvalancheBulletin: ...


def _registry_lookup_key(route: Route) -> str:
    return f"{route.region.country}:{route.region.name}"


@lru_cache
def load_avalanche_registry() -> dict[str, AvalancheRegionConfig]:
    raw: dict[str, Any] = json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
    out: dict[str, AvalancheRegionConfig] = {}
    for key, entry in raw.items():
        out[key] = AvalancheRegionConfig(
            region_key=str(entry["region_key"]),
            region_label=str(entry["region_label"]),
            adapter_id=entry.get("adapter_id"),
            official_bulletin_url=str(entry["official_bulletin_url"]),
            permitted_feed=bool(entry.get("permitted_feed", False)),
        )
    return out


def resolve_avalanche_region(route: Route) -> AvalancheRegionConfig | None:
    return load_avalanche_registry().get(_registry_lookup_key(route))


def assess_avalanche_freshness(bulletin: AvalancheBulletin, now: datetime) -> AvalancheFreshness:
    if now.tzinfo is None or now.utcoffset() != timedelta(0):
        raise ValueError("now must be UTC-aware")
    age = (now - bulletin.source_time).total_seconds()
    if age > bulletin.max_age_seconds:
        return AvalancheFreshness.STALE
    return AvalancheFreshness.OK


class MockAvalancheAdapter:
    adapter_version = MOCK_AVALANCHE_ADAPTER_VERSION

    def fetch_bulletin(
        self,
        *,
        route_id: UUID,
        region_key: str,
        adapter_id: str,
        plan_date: str,
    ) -> AvalancheBulletin:
        del adapter_id
        key = hash((str(route_id), region_key, plan_date)) % 1000
        registry = load_avalanche_registry()
        label = next(
            (cfg.region_label for cfg in registry.values() if cfg.region_key == region_key),
            region_key,
        )
        url = next(
            (
                cfg.official_bulletin_url
                for cfg in registry.values()
                if cfg.region_key == region_key
            ),
            "",
        )
        return AvalancheBulletin(
            region_key=region_key,
            region_label=label,
            summary=f"Regional bulletin summary for {region_key} (mock variant {key % 7}).",
            source_time=datetime.now(timezone.utc),
            official_bulletin_url=url,
        )


def build_avalanche_planning_input(
    route: Route,
    *,
    route_id: UUID,
    plan_date: str,
    now: datetime,
    port: AvalanchePort | None = None,
    bulletin_override: AvalancheBulletin | None = None,
) -> AvalanchePlanningInput:
    adapter = port or MockAvalancheAdapter()
    config = resolve_avalanche_region(route)
    if config is None:
        return AvalanchePlanningInput(
            freshness=AvalancheFreshness.UNKNOWN,
            assessment=AvalancheAssessmentKind.UNKNOWN,
            region_key="unconfigured",
            region_label=route.region.name,
            official_bulletin_url="",
            bulletin=None,
            adapter_version=adapter.adapter_version,
        )

    if not config.permitted_feed or config.adapter_id is None:
        return AvalanchePlanningInput(
            freshness=AvalancheFreshness.OK,
            assessment=AvalancheAssessmentKind.NOT_ASSESSED,
            region_key=config.region_key,
            region_label=config.region_label,
            official_bulletin_url=config.official_bulletin_url,
            bulletin=None,
            adapter_version=adapter.adapter_version,
        )

    bulletin = bulletin_override or adapter.fetch_bulletin(
        route_id=route_id,
        region_key=config.region_key,
        adapter_id=config.adapter_id,
        plan_date=plan_date,
    )
    freshness = assess_avalanche_freshness(bulletin, now)
    if freshness is AvalancheFreshness.STALE:
        return AvalanchePlanningInput(
            freshness=freshness,
            assessment=AvalancheAssessmentKind.UNKNOWN,
            region_key=config.region_key,
            region_label=config.region_label,
            official_bulletin_url=config.official_bulletin_url,
            bulletin=bulletin,
            adapter_version=adapter.adapter_version,
        )

    return AvalanchePlanningInput(
        freshness=freshness,
        assessment=AvalancheAssessmentKind.ASSESSED,
        region_key=config.region_key,
        region_label=config.region_label,
        official_bulletin_url=config.official_bulletin_url,
        bulletin=bulletin,
        adapter_version=adapter.adapter_version,
    )


def avalanche_component_payload(input_: AvalanchePlanningInput) -> dict[str, Any]:
    status = "ok"
    if input_.freshness is AvalancheFreshness.STALE:
        status = "degraded"
    elif input_.freshness is AvalancheFreshness.UNKNOWN:
        status = "unknown"

    payload: dict[str, Any] = {
        "status": status,
        "assessment": input_.assessment.value,
        "region_key": input_.region_key,
        "official_bulletin_url": input_.official_bulletin_url,
    }
    if input_.bulletin is not None and input_.assessment is AvalancheAssessmentKind.ASSESSED:
        payload["source_time"] = input_.bulletin.source_time.isoformat()
        payload["max_age_seconds"] = input_.bulletin.max_age_seconds
    return payload


def avalanche_response_payload(input_: AvalanchePlanningInput) -> dict[str, Any] | None:
    if input_.assessment is AvalancheAssessmentKind.NOT_ASSESSED:
        return {
            "assessment": input_.assessment.value,
            "region_key": input_.region_key,
            "region_label": input_.region_label,
            "official_bulletin_url": input_.official_bulletin_url,
        }
    if input_.assessment is AvalancheAssessmentKind.UNKNOWN:
        return {
            "assessment": input_.assessment.value,
            "region_key": input_.region_key,
            "region_label": input_.region_label,
            "official_bulletin_url": input_.official_bulletin_url,
        }
    if input_.bulletin is None:
        return None
    return {
        "assessment": input_.assessment.value,
        "region_key": input_.region_key,
        "region_label": input_.region_label,
        "summary": input_.bulletin.summary,
        "source_time": input_.bulletin.source_time.isoformat(),
        "max_age_seconds": input_.bulletin.max_age_seconds,
        "official_bulletin_url": input_.official_bulletin_url,
    }
