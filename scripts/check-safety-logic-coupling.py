#!/usr/bin/env python3
"""Block safety-logic edits unless tests change in the same diff (issue #62)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SAFETY_PATHS = (
    "backend/app/data/difficulty_mappings.json",
    "backend/app/planning/recommendation.py",
    "backend/app/planning/thunderstorm.py",
    "backend/app/planning/gear.py",
    "backend/app/domain/difficulty.py",
)
TEST_PREFIXES = ("backend/tests/", "oncall-worker/tests/")


def _changed_files(base: str) -> list[str]:
    proc = subprocess.run(
        ["git", "diff", "--name-only", base],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else "HEAD"
    changed = _changed_files(base)
    if not changed:
        return 0
    safety_touched = [path for path in changed if path.replace("\\", "/") in SAFETY_PATHS]
    if not safety_touched:
        return 0
    tests_touched = any(
        path.replace("\\", "/").startswith(TEST_PREFIXES) for path in changed
    )
    if tests_touched:
        return 0
    print(
        "Safety-logic files changed without test updates:",
        ", ".join(safety_touched),
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
