"""Plain-text wiki fields: strip control characters and markup delimiters."""

from __future__ import annotations

import re

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_ANGLE_BRACKETS = re.compile(r"[<>]")


def sanitize_free_text(value: str) -> str:
    """Return storage-safe plain text (no HTML/script delimiters or control chars)."""
    cleaned = _CONTROL_CHARS.sub("", value)
    cleaned = _ANGLE_BRACKETS.sub("", cleaned)
    return cleaned.strip()
