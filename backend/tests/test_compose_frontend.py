from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_compose_declares_frontend_service() -> None:
    compose = yaml.safe_load(
        (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    )
    frontend = compose["services"]["frontend"]
    assert frontend["build"]["context"] == "frontend"
    assert "127.0.0.1:5173:80" in frontend["ports"][0]
