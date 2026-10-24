from __future__ import annotations

import json
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
ALERT_PATH = (
    REPO_ROOT
    / "observability"
    / "grafana"
    / "provisioning"
    / "alerting"
    / "plan-failure-rate.yaml"
)
DASHBOARD_PATH = (
    REPO_ROOT
    / "observability"
    / "grafana"
    / "dashboards"
    / "climbit-planning-system.json"
)
DASHBOARD_PROVISION = (
    REPO_ROOT
    / "observability"
    / "grafana"
    / "provisioning"
    / "dashboards"
    / "default.yaml"
)

REQUIRED_ALERT_ANNOTATIONS = frozenset(
    {"service", "environment", "version", "owner", "dashboard_url"}
)


def _plan_failure_rule() -> dict:
    doc = yaml.safe_load(ALERT_PATH.read_text(encoding="utf-8"))
    groups = doc["groups"]
    for group in groups:
        for rule in group["rules"]:
            if rule.get("uid") == "climbit-plan-failure-rate":
                return rule
    raise AssertionError("climbit-plan-failure-rate rule not found")


def test_plan_failure_alert_declares_ownership_metadata() -> None:
    rule = _plan_failure_rule()
    assert rule["for"] == "5m"
    annotations = rule["annotations"]
    assert REQUIRED_ALERT_ANNOTATIONS <= set(annotations.keys())
    assert annotations["service"] == "climbit-api"
    assert "climbit-planning" in annotations["dashboard_url"]
    expr_blob = json.dumps(rule["data"])
    assert "climbit_plan_requests_total" in expr_blob
    assert "failure" in expr_blob


def test_dashboard_provisioned_with_planning_sections() -> None:
    provision = yaml.safe_load(DASHBOARD_PROVISION.read_text(encoding="utf-8"))
    assert provision["providers"][0]["options"]["path"] == "/etc/grafana/dashboards"
    dashboard = json.loads(DASHBOARD_PATH.read_text(encoding="utf-8"))
    assert dashboard["uid"] == "climbit-planning"
    titles = {
        panel["title"] for panel in dashboard["panels"] if panel.get("type") == "row"
    }
    assert titles >= {
        "API health",
        "Integrations",
        "Planning impact",
        "Wiki activity",
    }
