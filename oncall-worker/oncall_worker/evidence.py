from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class EvidenceRecord:
    alert_rule_uid: str
    alert_title: str
    fingerprint: str
    firing_starts_at: str
    annotations: dict[str, str]
    evidence_consulted: list[str]
    commands_run: list[dict[str, Any]]
    changed_files: list[str]
    commit_hash: str | None
    outcome: str
    branch_name: str
    created_at: str = field(
        default_factory=lambda: datetime.now(tz=UTC).isoformat(timespec="seconds")
    )

    def validate(self) -> None:
        required = [
            self.alert_rule_uid,
            self.fingerprint,
            self.outcome,
            self.branch_name,
        ]
        if not all(required):
            raise ValueError("evidence record missing required fields")
        if not self.commands_run:
            raise ValueError("evidence record must list commands_run")
        if not self.evidence_consulted:
            raise ValueError("evidence record must list evidence_consulted")

    def to_markdown(self) -> str:
        lines = [
            f"# On-call session evidence — {self.alert_title}",
            "",
            f"- **Created:** {self.created_at}",
            f"- **Branch:** `{self.branch_name}`",
            f"- **Rule UID:** `{self.alert_rule_uid}`",
            f"- **Fingerprint:** `{self.fingerprint}`",
            f"- **Firing since:** {self.firing_starts_at}",
            "",
            "## Annotations",
            "",
        ]
        for key, value in sorted(self.annotations.items()):
            lines.append(f"- **{key}:** {value}")
        lines.extend(["", "## Evidence consulted", ""])
        lines.extend(f"- {item}" for item in self.evidence_consulted)
        lines.extend(["", "## Commands / tests", ""])
        for entry in self.commands_run:
            cmd = entry.get("command", "")
            exit_code = entry.get("exit_code")
            lines.append(f"- `{cmd}` → exit {exit_code}")
        if self.changed_files:
            lines.extend(["", "## Changed files", ""])
            lines.extend(f"- `{path}`" for path in self.changed_files)
        if self.commit_hash:
            lines.append("")
            lines.append(f"**Commit:** `{self.commit_hash}`")
        lines.extend(["", "## Outcome", "", self.outcome, ""])
        return "\n".join(lines)

    def write(self, directory: Path, *, slug: str) -> Path:
        self.validate()
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"oncall-{slug}.md"
        path.write_text(self.to_markdown(), encoding="utf-8")
        meta = directory / f"oncall-{slug}.json"
        meta.write_text(
            __import__("json").dumps(asdict(self), indent=2),
            encoding="utf-8",
        )
        return path
