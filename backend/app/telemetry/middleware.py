from __future__ import annotations

from fastapi import Request, Response

from app.telemetry.tracing import current_trace_id, plan_build_trace

_TRACE_ID_HEADER = "X-Trace-Id"


def _is_plan_create_request(request: Request) -> bool:
    return request.method == "POST" and request.url.path.endswith("/plans")


async def trace_plan_http_requests(request: Request, call_next) -> Response:
    if not _is_plan_create_request(request):
        return await call_next(request)
    with plan_build_trace():
        response = await call_next(request)
        trace_id = current_trace_id()
        if trace_id:
            response.headers[_TRACE_ID_HEADER] = trace_id
        return response
