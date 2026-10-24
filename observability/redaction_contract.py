"""Contract helper: mirrors collector redaction key/value rules for tests only."""

from __future__ import annotations

import json
import re
from typing import Any


def _compile(patterns: list[str]) -> list[re.Pattern[str]]:
    return [re.compile(pattern) for pattern in patterns]


def apply_redaction_policy(attributes: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    key_pattern = re.compile(str(policy["sensitive_key_pattern"]))
    value_patterns = _compile(list(policy.get("sensitive_value_patterns") or []))
    redacted: dict[str, Any] = {}
    for key, value in attributes.items():
        key_str = str(key)
        if key_pattern.search(key_str):
            continue
        value_str = value if isinstance(value, str) else json.dumps(value, ensure_ascii=True)
        if any(pattern.search(value_str) for pattern in value_patterns):
            continue
        redacted[key] = value
    return redacted
