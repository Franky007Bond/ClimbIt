from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_agent_modular_docs_exist() -> None:
    for name in (
        "workflow.md",
        "team-roles.md",
        "source-onboarding.md",
        "route-data-review.md",
        "operations.md",
        "permissions.md",
    ):
        assert (REPO_ROOT / "_docs" / "agent" / name).is_file()


def test_mcp_search_routes_read_only() -> None:
    from app.agent_readonly.tools import mcp_write_enabled, search_routes

    assert mcp_write_enabled() is False
    payload = search_routes(limit=3)
    assert payload["count"] >= 1
    assert "routes" in payload


def test_safety_guardrail_passes_on_clean_tree() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "check-safety-logic-coupling.py"),
            "HEAD",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr


def test_mcp_stdio_tool() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "app.agent_mcp"],
        cwd=REPO_ROOT / "backend",
        input=json.dumps({"id": 1, "tool": "get_gear_list", "arguments": {}}) + "\n",
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    line = proc.stdout.strip().splitlines()[-1]
    payload = json.loads(line)
    assert "result" in payload
