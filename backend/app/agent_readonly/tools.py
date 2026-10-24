from __future__ import annotations

import os
from typing import Any

from app.planning.versions import GEAR_RULES_VERSION
from app.planning.versions import PLANNING_RULES_VERSION


def mcp_write_enabled() -> bool:
    raw = os.environ.get("CLIMBIT_MCP_WRITE_ENABLED", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def search_routes(*, limit: int = 10) -> dict[str, Any]:
    """Return published route ids and names from seed metadata (no DB required)."""
    from app.data.seed_routes import build_seed_routes

    routes = [
        {"id": str(route_id), "name": route.name}
        for route_id, route in build_seed_routes()
    ][: max(1, min(limit, 50))]
    return {"routes": routes, "count": len(routes)}


def get_route(route_id: str) -> dict[str, Any]:
    return {
        "route_id": route_id,
        "status": "lookup_via_api",
        "hint": f"GET /routes/{route_id}",
    }


def get_plan_hint(route_id: str) -> dict[str, Any]:
    return {
        "route_id": route_id,
        "hint": f"POST /routes/{route_id}/plans with date and origin",
        "recommendation_rules_version": PLANNING_RULES_VERSION,
    }


def get_gear_list() -> dict[str, Any]:
    return {"gear_rules_version": GEAR_RULES_VERSION}


def get_transit_options() -> dict[str, Any]:
    adapter = os.environ.get("TRANSIT_ADAPTER", "mock")
    return {"adapter": adapter, "write_enabled": mcp_write_enabled()}
