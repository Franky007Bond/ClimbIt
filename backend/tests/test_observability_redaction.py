from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from observability.redaction_contract import apply_redaction_policy

REPO_ROOT = Path(__file__).resolve().parents[2]
COLLECTOR_CONFIG = REPO_ROOT / "observability" / "otel-collector-config.yaml"
LOKI_CONFIG = REPO_ROOT / "observability" / "loki.yaml"
TEMPO_CONFIG = REPO_ROOT / "observability" / "tempo.yaml"

SENSITIVE_ORIGIN = "Munich Hauptbahnhof platform 11"
SENSITIVE_AUTH = "Bearer plan-integration-test-token"
SENSITIVE_BODY = json.dumps({"origin": SENSITIVE_ORIGIN, "plan_date": "2026-07-15"})


@pytest.fixture(scope="module")
def collector_config() -> dict:
    return yaml.safe_load(COLLECTOR_CONFIG.read_text(encoding="utf-8"))


def test_collector_config_declares_redaction_sampling_and_pipelines(
    collector_config: dict,
) -> None:
    processors = collector_config["processors"]
    assert "transform/redaction" in processors
    assert "probabilistic_sampler" in processors
    service = collector_config["service"]
    for signal in ("traces", "metrics", "logs"):
        pipeline = service["pipelines"][signal]
        assert "transform/redaction" in pipeline["processors"]


def test_loki_and_tempo_retention_about_seven_days() -> None:
    loki = yaml.safe_load(LOKI_CONFIG.read_text(encoding="utf-8"))
    tempo = yaml.safe_load(TEMPO_CONFIG.read_text(encoding="utf-8"))
    assert loki["limits_config"]["retention_period"] == "168h"
    assert tempo["compactor"]["compaction"]["block_retention"] == "168h"


def test_redaction_policy_removes_origin_authorization_and_body_from_exported_attributes(
    collector_config: dict,
) -> None:
    policy = yaml.safe_load(
        (REPO_ROOT / "observability" / "redaction-policy.yaml").read_text(
            encoding="utf-8"
        )
    )
    attributes = {
        "http.request.header.authorization": SENSITIVE_AUTH,
        "plan.origin": SENSITIVE_ORIGIN,
        "http.request.body": SENSITIVE_BODY,
        "trace_id": "a" * 32,
        "planning.step": "weather",
    }
    redacted = apply_redaction_policy(attributes, policy)
    exported = json.dumps(redacted, ensure_ascii=True)
    assert SENSITIVE_AUTH not in exported
    assert SENSITIVE_ORIGIN not in exported
    assert "Hauptbahnhof" not in exported
    assert redacted["trace_id"] == "a" * 32
    assert redacted["planning.step"] == "weather"


@pytest.mark.skipif(shutil.which("docker") is None, reason="docker not available")
def test_collector_config_validates_in_contrib_image() -> None:
    result = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{REPO_ROOT / 'observability'}:/cfg",
            "otel/opentelemetry-collector-contrib:0.114.0",
            "validate",
            "--config=/cfg/otel-collector-config.yaml",
        ],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_compose_observability_file_declares_profile() -> None:
    compose = yaml.safe_load(
        (REPO_ROOT / "docker-compose.observability.yml").read_text(encoding="utf-8")
    )
    services = compose["services"]
    assert "otel-collector" in services
    assert services["otel-collector"]["profiles"] == ["observability"]
    prometheus_retention = " ".join(services["prometheus"]["command"])
    assert "168h" in prometheus_retention
    api_env = services["api"]["environment"]
    assert api_env["OTEL_EXPORTER_OTLP_ENDPOINT"] == "http://otel-collector:4318"
