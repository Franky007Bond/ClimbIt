from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_deployment_workflows_and_evidence_exist() -> None:
    assert (REPO_ROOT / "_docs" / "operations" / "deployment.md").is_file()
    assert (
        REPO_ROOT
        / "_docs"
        / "operations"
        / "evidence"
        / "deploy-rollback-2026-10-24.md"
    ).is_file()
    assert (REPO_ROOT / ".github" / "workflows" / "deploy-dev.yml").is_file()
    assert (REPO_ROOT / ".github" / "workflows" / "deploy-prod.yml").is_file()
    assert (REPO_ROOT / "scripts" / "rollback-compose.sh").is_file()
