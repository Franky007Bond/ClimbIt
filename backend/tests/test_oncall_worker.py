"""Contract tests for the on-call worker package (issue #61)."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ONCALL_ROOT = REPO_ROOT / "oncall-worker"
if str(ONCALL_ROOT) not in sys.path:
    sys.path.insert(0, str(ONCALL_ROOT))

from oncall_worker.alerts import FiringAlert, branch_alert_id  # noqa: E402


def test_oncall_runbook_and_demo_evidence_exist() -> None:
    runbook = REPO_ROOT / "_docs" / "operations" / "oncall-responder.md"
    demo = (
        REPO_ROOT
        / "_docs"
        / "operations"
        / "evidence"
        / "oncall-climbit-plan-failure-rate-2026-10-24.md"
    )
    compose = REPO_ROOT / "docker-compose.observability.yml"
    text = compose.read_text(encoding="utf-8")
    assert runbook.is_file()
    assert demo.is_file()
    assert "oncall-worker" in text
    assert branch_alert_id(
        FiringAlert(
            rule_uid="climbit-plan-failure-rate",
            rule_title="t",
            fingerprint="0123456789abcdef",
            starts_at="",
            annotations={},
            labels={},
        )
    ).startswith("climbit-plan-failure-rate-")
