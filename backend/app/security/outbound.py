"""Outbound HTTP: only configured integration hosts (never user-supplied URLs)."""

from __future__ import annotations

import os
from urllib.parse import urlparse

DEFAULT_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
DEFAULT_TRANSITOUS_PLAN_URL = "https://api.transitous.org/api/v1/plan"


def configured_integration_hosts() -> frozenset[str]:
    hosts: set[str] = set()
    for env_name, default in (
        ("OVERPASS_API_URL", DEFAULT_OVERPASS_URL),
        ("TRANSITOUS_PLAN_URL", DEFAULT_TRANSITOUS_PLAN_URL),
    ):
        raw = os.environ.get(env_name, default).strip() or default
        parsed = urlparse(raw)
        if parsed.hostname:
            hosts.add(parsed.hostname.lower())
    return frozenset(hosts)


def assert_allowed_outbound_url(url: str) -> None:
    """Raise ValueError when url is not an configured integration endpoint."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("outbound URL must be an http(s) URL with a host")
    host = parsed.hostname.lower()
    if host not in configured_integration_hosts():
        raise ValueError(f"outbound host {host!r} is not an allowed integration host")
