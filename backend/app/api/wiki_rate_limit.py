from __future__ import annotations

import os
import time
from collections import defaultdict
from collections import deque

from fastapi import HTTPException, Request

_BUCKETS: dict[str, deque[float]] = defaultdict(deque)


def reset_wiki_anonymous_rate_limit_buckets() -> None:
    _BUCKETS.clear()


def _limit_max() -> int:
    return int(os.environ.get("WIKI_ANONYMOUS_EDIT_RATE_LIMIT_MAX", "20"))


def _limit_window_seconds() -> int:
    return int(os.environ.get("WIKI_ANONYMOUS_EDIT_RATE_LIMIT_WINDOW_SECONDS", "3600"))


def enforce_wiki_anonymous_rate_limit(request: Request) -> None:
    if request.client is None:
        client_ip = "unknown"
    else:
        client_ip = request.client.host
    now = time.time()
    window = _limit_window_seconds()
    bucket = _BUCKETS[client_ip]
    while bucket and bucket[0] <= now - window:
        bucket.popleft()
    if len(bucket) >= _limit_max():
        retry_after = max(1, int(window - (now - bucket[0])))
        raise HTTPException(
            status_code=429,
            detail={"code": "rate_limit_exceeded"},
            headers={"Retry-After": str(retry_after)},
        )
    bucket.append(now)
