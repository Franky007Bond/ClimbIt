from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any
from typing import Protocol

from app.osm.manifest import OsmElementType

logger = logging.getLogger(__name__)

DEFAULT_OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"
DEFAULT_OVERPASS_MIN_INTERVAL_SECONDS = 2.0
OVERPASS_HTTP_TIMEOUT_SECONDS = 60
MAX_OVERPASS_RETRIES = 3
INITIAL_RETRY_BACKOFF_SECONDS = 2.0


class OverpassError(Exception):
    pass


class OverpassHttpStatusError(OverpassError):
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        super().__init__(f"Overpass HTTP {status_code}")


class OverpassClient(Protocol):
    def fetch_element(self, osm_type: OsmElementType, osm_id: int) -> dict[str, Any]: ...


def overpass_api_url() -> str:
    return os.environ.get("OVERPASS_API_URL", DEFAULT_OVERPASS_API_URL)


def overpass_min_interval_seconds() -> float:
    raw = os.environ.get(
        "OVERPASS_MIN_INTERVAL_SECONDS",
        str(DEFAULT_OVERPASS_MIN_INTERVAL_SECONDS),
    )
    return float(raw)


def _build_query(osm_type: OsmElementType, osm_id: int) -> str:
    return f"[out:json][timeout:25];{osm_type.value}({osm_id});out geom;"


@dataclass
class UrllibOverpassClient:
    api_url: str
    min_interval_seconds: float
    _last_request_at: float | None = None

    def fetch_element(self, osm_type: OsmElementType, osm_id: int) -> dict[str, Any]:
        if self._last_request_at is not None:
            elapsed = time.monotonic() - self._last_request_at
            wait = self.min_interval_seconds - elapsed
            if wait > 0:
                time.sleep(wait)

        query = _build_query(osm_type, osm_id)
        logger.debug("overpass request for %s %s", osm_type.value, osm_id)
        payload = self._post_with_retries(query)
        self._last_request_at = time.monotonic()
        return payload

    def _post_with_retries(self, query: str) -> dict[str, Any]:
        backoff = INITIAL_RETRY_BACKOFF_SECONDS
        last_error: Exception | None = None
        for attempt in range(MAX_OVERPASS_RETRIES + 1):
            try:
                return _post_overpass_query(self.api_url, query)
            except OverpassHttpStatusError as exc:
                last_error = exc
                if exc.status_code not in (429, 504) or attempt >= MAX_OVERPASS_RETRIES:
                    raise
                logger.warning(
                    "overpass retry after HTTP %s (attempt %s)",
                    exc.status_code,
                    attempt + 1,
                )
                time.sleep(backoff)
                backoff *= 2
        assert last_error is not None
        raise last_error


def _post_overpass_query(api_url: str, query: str) -> dict[str, Any]:
    body = query.encode("utf-8")
    request = urllib.request.Request(
        api_url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(request, timeout=OVERPASS_HTTP_TIMEOUT_SECONDS) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        raise OverpassHttpStatusError(exc.code) from exc
    except urllib.error.URLError as exc:
        msg = "Overpass request failed"
        raise OverpassError(msg) from exc

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        msg = "Overpass response is not valid JSON"
        raise OverpassError(msg) from exc
    if not isinstance(payload, dict):
        msg = "Overpass response must be a JSON object"
        raise OverpassError(msg)
    return payload
