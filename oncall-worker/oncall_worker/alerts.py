from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class FiringAlert:
    rule_uid: str
    rule_title: str
    fingerprint: str
    starts_at: str
    annotations: dict[str, str]
    labels: dict[str, str]


class AlertSource(Protocol):
    def list_firing(self) -> list[FiringAlert]: ...


def branch_alert_id(alert: FiringAlert) -> str:
    suffix = "".join(ch for ch in alert.fingerprint.lower() if ch.isalnum())[:8]
    uid = "".join(ch for ch in alert.rule_uid if ch.isalnum() or ch in "-_")
    return f"{uid}-{suffix or 'unknown'}"


class GrafanaAlertSource:
    """Read firing alerts from Grafana Alertmanager (Unified Alerting)."""

    def __init__(self, *, base_url: str, token: str | None) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token

    def list_firing(self) -> list[FiringAlert]:
        url = f"{self._base_url}/api/alertmanager/grafana/api/v2/alerts"
        request = urllib.request.Request(url, method="GET")
        if self._token:
            request.add_header("Authorization", f"Bearer {self._token}")
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError:
            return []
        alerts: list[FiringAlert] = []
        for item in payload:
            status = item.get("status", {})
            if status.get("state") != "active":
                continue
            labels = {str(k): str(v) for k, v in item.get("labels", {}).items()}
            annotations = {
                str(k): str(v) for k, v in item.get("annotations", {}).items()
            }
            rule_uid = labels.get("rule_uid") or labels.get("grafana_rule_uid") or ""
            if not rule_uid:
                rule_uid = labels.get("alertname", "unknown-rule")
            alerts.append(
                FiringAlert(
                    rule_uid=rule_uid,
                    rule_title=labels.get("alertname", rule_uid),
                    fingerprint=str(item.get("fingerprint", "")),
                    starts_at=str(status.get("startsAt", "")),
                    annotations=annotations,
                    labels=labels,
                )
            )
        return alerts


class StaticAlertSource:
    """Deterministic alerts for tests and dry-run demos."""

    def __init__(self, alerts: list[FiringAlert]) -> None:
        self._alerts = alerts

    def list_firing(self) -> list[FiringAlert]:
        return list(self._alerts)
