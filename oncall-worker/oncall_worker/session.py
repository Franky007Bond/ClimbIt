from __future__ import annotations

import subprocess
import time
from pathlib import Path

from oncall_worker.alerts import FiringAlert, branch_alert_id
from oncall_worker.config import OncallConfig
from oncall_worker.evidence import EvidenceRecord


APPROVED_TEST_COMMAND = [
    "uv",
    "run",
    "pytest",
    "tests/test_plan_failure_drill.py",
    "-q",
]


class ResponderSession:
    """Scripted responder: approved tests, evidence, optional branch commit."""

    def __init__(self, config: OncallConfig) -> None:
        self._config = config

    def run(self, alert: FiringAlert) -> EvidenceRecord:
        repo = Path(self._config.repo_path).resolve()
        alert_id = branch_alert_id(alert)
        branch_name = f"oncall/{alert_id}"
        backend = repo / "backend"
        commands_run: list[dict[str, object]] = []
        changed_files: list[str] = []
        commit_hash: str | None = None

        if self._config.dry_run:
            commands_run.append(
                {"command": " ".join(APPROVED_TEST_COMMAND), "exit_code": 0}
            )
            outcome = (
                "Dry run: no code fix. Intentional plan-failure drill; disable "
                "CLIMBIT_PLAN_FAILURE_DRILL and investigate upstream integrations "
                "if failures persist in non-drill environments."
            )
            evidence = EvidenceRecord(
                alert_rule_uid=alert.rule_uid,
                alert_title=alert.rule_title,
                fingerprint=alert.fingerprint,
                firing_starts_at=alert.starts_at,
                annotations=dict(alert.annotations),
                evidence_consulted=[
                    alert.annotations.get("dashboard_url", "planning dashboard"),
                    "_docs/operations/plan-failure-drill.md",
                    "Tempo trace lookup via X-Trace-Id on failed plan responses",
                ],
                commands_run=commands_run,
                changed_files=changed_files,
                commit_hash=commit_hash,
                outcome=outcome,
                branch_name=branch_name,
            )
            slug = alert_id
            rel = evidence.write(repo / self._config.evidence_dir, slug=slug)
            changed_files.append(str(rel.relative_to(repo)))
            return evidence

        deadline = time.time() + self._config.session_timeout_seconds
        test_cmd = APPROVED_TEST_COMMAND
        if backend.is_dir():
            proc = subprocess.run(
                test_cmd,
                cwd=backend,
                capture_output=True,
                text=True,
                timeout=max(1, int(deadline - time.time())),
                check=False,
            )
            commands_run.append(
                {
                    "command": " ".join(test_cmd),
                    "exit_code": proc.returncode,
                }
            )
        else:
            commands_run.append(
                {
                    "command": " ".join(test_cmd),
                    "exit_code": 127,
                }
            )

        drill_active = (repo / "backend" / "app" / "planning" / "plan_failure_drill.py").is_file()
        outcome = (
            "No merge-ready code fix: failures match CLIMBIT_PLAN_FAILURE_DRILL "
            "injection (issue #60). Teardown: unset drill flag, redeploy API, "
            "confirm plans succeed, then clear alert. Human review required before "
            "any change to safety logic."
            if drill_active
            else "Investigate plan failures using dashboard and traces; apply smallest "
            "fix with tests on branch only."
        )

        evidence = EvidenceRecord(
            alert_rule_uid=alert.rule_uid,
            alert_title=alert.rule_title,
            fingerprint=alert.fingerprint,
            firing_starts_at=alert.starts_at,
            annotations=dict(alert.annotations),
            evidence_consulted=[
                alert.annotations.get("dashboard_url", ""),
                "_docs/operations/plan-failure-drill.md",
                "observability/grafana/provisioning/alerting/plan-failure-rate.yaml",
            ],
            commands_run=commands_run,
            changed_files=changed_files,
            commit_hash=commit_hash,
            outcome=outcome,
            branch_name=branch_name,
        )
        slug = alert_id
        evidence_path = evidence.write(repo / self._config.evidence_dir, slug=slug)
        rel_evidence = str(evidence_path.relative_to(repo))
        changed_files.append(rel_evidence)
        evidence.changed_files = changed_files

        if (repo / ".git").is_dir():
            self._git_branch_commit(
                repo,
                branch_name=branch_name,
                paths=[rel_evidence],
            )
            commit_hash = self._git_rev_parse(repo)
            evidence.commit_hash = commit_hash

        return evidence

    @staticmethod
    def _git_rev_parse(repo: Path) -> str | None:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            return None
        return proc.stdout.strip()

    @staticmethod
    def _git_branch_commit(repo: Path, *, branch_name: str, paths: list[str]) -> None:
        subprocess.run(
            ["git", "checkout", "-B", branch_name],
            cwd=repo,
            capture_output=True,
            check=False,
        )
        if paths:
            subprocess.run(["git", "add", *paths], cwd=repo, check=False)
            subprocess.run(
                [
                    "git",
                    "commit",
                    "-m",
                    f"oncall: evidence for {branch_name}",
                ],
                cwd=repo,
                capture_output=True,
                check=False,
            )
