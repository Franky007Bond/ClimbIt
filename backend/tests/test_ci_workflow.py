from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
CI_DOC = REPO_ROOT / "_docs" / "ci.md"

REQUIRED_JOBS = frozenset(
    {
        "backend-lint",
        "backend-unit",
        "backend-integration",
        "backend-contract",
        "frontend",
        "image-build",
        "security-scan",
    }
)


def test_ci_workflow_declares_required_jobs() -> None:
    workflow = yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))
    assert REQUIRED_JOBS <= set(workflow["jobs"])


def test_ci_documentation_includes_failing_check_example() -> None:
    text = CI_DOC.read_text(encoding="utf-8")
    assert "failing check" in text.lower() or "failing-check" in text.lower()
    assert "backend-lint" in text
    assert "exit code" in text.lower()
