import json
import logging
import sys

from fastapi import Request, Response

from app.telemetry.metrics import http_route_template
from app.telemetry.metrics import record_http_request
from app.telemetry.metrics import record_plan_request
from app.telemetry.metrics import record_wiki_request
from app.telemetry.metrics import wiki_operation_for_request
from app.telemetry.tracing import current_trace_id

ACCESS_LOGGER_NAME = "app.access"
PLANNING_LOGGER_NAME = "app.planning"
_PROBE_PATHS = frozenset({"/health", "/ready"})
_JSON_HANDLER_MARK = "_climbit_json_handler"


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "level": record.levelname,
            "logger": record.name,
        }
        method = getattr(record, "method", None)
        path = getattr(record, "path", None)
        status_code = getattr(record, "status_code", None)
        if method is not None:
            payload["method"] = method
        if path is not None:
            payload["path"] = path
        if status_code is not None:
            payload["status_code"] = status_code
        message = record.getMessage()
        if message:
            payload["message"] = message
        trace_id = getattr(record, "trace_id", None) or current_trace_id()
        if trace_id:
            payload["trace_id"] = trace_id
        event = getattr(record, "event", None)
        if event is not None:
            payload["event"] = event
        return json.dumps(payload, ensure_ascii=True)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter())
    setattr(handler, _JSON_HANDLER_MARK, True)

    root = logging.getLogger()
    if not any(
        getattr(existing, _JSON_HANDLER_MARK, False) for existing in root.handlers
    ):
        root.addHandler(handler)
    if root.level == logging.NOTSET or root.level > logging.INFO:
        root.setLevel(logging.INFO)

    for name in ("uvicorn", "uvicorn.error"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True
        logger.setLevel(logging.INFO)

    access = logging.getLogger("uvicorn.access")
    access.handlers.clear()
    access.propagate = False
    access.disabled = True
    access.setLevel(logging.CRITICAL)


async def log_http_access(request: Request, call_next) -> Response:
    response = await call_next(request)
    path = request.url.path
    if path not in _PROBE_PATHS:
        trace_id = current_trace_id()
        if trace_id is None:
            header_trace = response.headers.get("X-Trace-Id")
            if header_trace:
                trace_id = header_trace
        extra: dict[str, object] = {
            "method": request.method,
            "path": path,
            "status_code": response.status_code,
        }
        if trace_id is not None:
            extra["trace_id"] = trace_id
        logging.getLogger(ACCESS_LOGGER_NAME).info(
            "request",
            extra=extra,
        )
        route_template = http_route_template(path)
        record_http_request(
            route=route_template,
            method=request.method,
            status_code=response.status_code,
        )
        if (
            route_template == "/routes/{route_id}/plans"
            and request.method.upper() == "POST"
        ):
            record_plan_request(status_code=response.status_code)
        wiki_operation = wiki_operation_for_request(request.method, path)
        if wiki_operation is not None:
            record_wiki_request(
                operation=wiki_operation,
                status_code=response.status_code,
            )
    return response
