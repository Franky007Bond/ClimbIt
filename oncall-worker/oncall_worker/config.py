from __future__ import annotations

import os
from dataclasses import dataclass


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    return int(raw)


@dataclass(frozen=True)
class OncallConfig:
    grafana_url: str
    grafana_token: str | None
    repo_path: str
    poll_interval_seconds: int
    cooldown_seconds: int
    session_timeout_seconds: int
    state_path: str
    evidence_dir: str
    dry_run: bool

    @classmethod
    def from_environ(cls) -> OncallConfig:
        dry_raw = os.environ.get("ONCALL_DRY_RUN", "").strip().lower()
        return cls(
            grafana_url=os.environ.get(
                "ONCALL_GRAFANA_URL", "http://127.0.0.1:3000"
            ).rstrip("/"),
            grafana_token=os.environ.get("ONCALL_GRAFANA_TOKEN") or None,
            repo_path=os.environ.get("ONCALL_REPO_PATH", "."),
            poll_interval_seconds=_int_env("ONCALL_POLL_INTERVAL_SECONDS", 60),
            cooldown_seconds=_int_env("ONCALL_COOLDOWN_SECONDS", 900),
            session_timeout_seconds=_int_env("ONCALL_SESSION_TIMEOUT_SECONDS", 900),
            state_path=os.environ.get("ONCALL_STATE_PATH", ".oncall/state.json"),
            evidence_dir=os.environ.get(
                "ONCALL_EVIDENCE_DIR", "_docs/operations/evidence"
            ),
            dry_run=dry_raw in {"1", "true", "yes", "on"},
        )
