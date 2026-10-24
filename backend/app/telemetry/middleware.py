from __future__ import annotations

from fastapi import Request, Response

from app.telemetry.tracing import plan_build_trace


def _is_plan_create_request(request: Request) -> bool:
    return request.method == "POST" and request.url.path.endswith("/plans")


async def trace_plan_http_requests(request: Request, call_next) -> Response:
    if not _is_plan_create_request(request):
        return await call_next(request)
    with plan_build_trace():
        return await call_next(request)
