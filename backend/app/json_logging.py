import json
import logging
import sys

from fastapi import Request, Response

ACCESS_LOGGER_NAME = "app.access"
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
        return json.dumps(payload, ensure_ascii=True)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter())
    setattr(handler, _JSON_HANDLER_MARK, True)

    root = logging.getLogger()
    if not any(getattr(existing, _JSON_HANDLER_MARK, False) for existing in root.handlers):
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
        logging.getLogger(ACCESS_LOGGER_NAME).info(
            "request",
            extra={
                "method": request.method,
                "path": path,
                "status_code": response.status_code,
            },
        )
    return response
