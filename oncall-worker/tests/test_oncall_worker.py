from __future__ import annotations

import json
import shutil
import time
import uuid
from pathlib import Path

from oncall_worker.alerts import FiringAlert, StaticAlertSource, branch_alert_id
from oncall_worker.config import OncallConfig
from oncall_worker.dedup import CooldownStore
from oncall_worker.evidence import EvidenceRecord
from oncall_worker.worker import OncallWorker


def _sample_alert(*, fingerprint: str = "abc123def456") -> FiringAlert:
    return FiringAlert(
        rule_uid="climbit-plan-failure-rate",
        rule_title="Trip plan failure rate above 5%",
        fingerprint=fingerprint,
        starts_at="2026-10-24T20:00:00Z",
        annotations={
            "service": "climbit-api",
            "environment": "local",
            "owner": "platform-oncall",
            "dashboard_url": "http://127.0.0.1:3000/d/climbit-planning/climbit-planning-system",
        },
        labels={"alertname": "TripPlanFailureRate"},
    )


def test_branch_alert_id_is_filesystem_safe() -> None:
    alert = _sample_alert(fingerprint="fp/with spaces!")
    assert branch_alert_id(alert) == "climbit-plan-failure-rate-fpwithsp"


def _local_tmp() -> Path:
    path = Path(__file__).resolve().parent / f"_tmp-{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_cooldown_blocks_duplicate_session() -> None:
    tmp_path = _local_tmp()
    try:
        store = CooldownStore(tmp_path / "state.json", cooldown_seconds=900)
        assert store.should_start("fp1") is True
        store.mark_started("fp1")
        assert store.should_start("fp1") is False
        store.mark_finished("fp1")
        assert store.should_start("fp1") is False
        store._entries["fp1"].last_session_started_at = time.time() - 901
        assert store.should_start("fp1") is True
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_evidence_record_requires_fields() -> None:
    tmp_path = _local_tmp()
    try:
        record = EvidenceRecord(
            alert_rule_uid="uid",
            alert_title="title",
            fingerprint="fp",
            firing_starts_at="t",
            annotations={},
            evidence_consulted=["dashboard"],
            commands_run=[{"command": "uv run pytest", "exit_code": 0}],
            changed_files=[],
            commit_hash=None,
            outcome="no fix",
            branch_name="oncall/uid-abc",
        )
        path = record.write(tmp_path, slug="demo")
        assert path.is_file()
        payload = json.loads((tmp_path / "oncall-demo.json").read_text(encoding="utf-8"))
        assert payload["fingerprint"] == "fp"
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_worker_starts_one_session_per_poll() -> None:
    tmp_path = _local_tmp()
    try:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "backend").mkdir()
        config = OncallConfig(
            grafana_url="http://example.invalid",
            grafana_token=None,
            repo_path=str(repo),
            poll_interval_seconds=1,
            cooldown_seconds=900,
            session_timeout_seconds=60,
            state_path=".oncall/state.json",
            evidence_dir="_docs/operations/evidence",
            dry_run=True,
        )
        source = StaticAlertSource(
            [_sample_alert(), _sample_alert(fingerprint="other")]
        )
        worker = OncallWorker(config, alert_source=source)
        branches = worker.process_once()
        assert len(branches) == 2
        evidence_files = list((repo / "_docs/operations/evidence").glob("oncall-*.md"))
        assert len(evidence_files) == 2
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)
