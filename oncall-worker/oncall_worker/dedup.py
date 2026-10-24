from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FingerprintState:
    last_session_started_at: float
    active: bool


class CooldownStore:
    """Track fingerprint cooldown and in-flight sessions."""

    def __init__(self, path: Path, *, cooldown_seconds: int) -> None:
        self._path = path
        self._cooldown_seconds = cooldown_seconds
        self._entries: dict[str, FingerprintState] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.is_file():
            return
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        for fingerprint, item in raw.items():
            self._entries[fingerprint] = FingerprintState(
                last_session_started_at=float(item["last_session_started_at"]),
                active=bool(item["active"]),
            )

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            fingerprint: {
                "last_session_started_at": state.last_session_started_at,
                "active": state.active,
            }
            for fingerprint, state in self._entries.items()
        }
        self._path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def should_start(self, fingerprint: str) -> bool:
        if not fingerprint:
            return False
        state = self._entries.get(fingerprint)
        if state is None:
            return True
        if state.active:
            return False
        elapsed = time.time() - state.last_session_started_at
        return elapsed >= self._cooldown_seconds

    def mark_started(self, fingerprint: str) -> None:
        self._entries[fingerprint] = FingerprintState(
            last_session_started_at=time.time(),
            active=True,
        )
        self.save()

    def mark_finished(self, fingerprint: str) -> None:
        state = self._entries.get(fingerprint)
        if state is None:
            return
        state.active = False
        state.last_session_started_at = time.time()
        self.save()
