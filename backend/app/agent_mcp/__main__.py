from __future__ import annotations

import json
import sys

from app.agent_readonly.tools import (
    get_gear_list,
    get_plan_hint,
    get_route,
    get_transit_options,
    mcp_write_enabled,
    search_routes,
)

TOOLS = {
    "search_routes": lambda args: search_routes(limit=int(args.get("limit", 10))),
    "get_route": lambda args: get_route(str(args["route_id"])),
    "get_plan": lambda args: get_plan_hint(str(args["route_id"])),
    "get_gear_list": lambda _args: get_gear_list(),
    "get_transit_options": lambda _args: get_transit_options(),
}


def _write(message: dict) -> None:
    sys.stdout.write(json.dumps(message) + "\n")
    sys.stdout.flush()


def main() -> None:
    if mcp_write_enabled():
        _write({"error": "write tools are disabled in production configuration"})
        raise SystemExit(1)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        request = json.loads(line)
        tool = request.get("tool")
        args = request.get("arguments") or {}
        if tool not in TOOLS:
            _write({"id": request.get("id"), "error": f"unknown tool {tool}"})
            continue
        result = TOOLS[tool](args)
        _write({"id": request.get("id"), "result": result})


if __name__ == "__main__":
    main()
