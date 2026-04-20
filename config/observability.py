import logging
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from time import perf_counter

from django.conf import settings


_request_context = ContextVar("request_context", default={})


def get_request_context() -> dict:
    context = _request_context.get({})
    if not isinstance(context, dict):
        return {}
    return dict(context)


def get_current_request_id(default: str = "") -> str:
    context = get_request_context()
    request_id = context.get("request_id")
    if request_id:
        return str(request_id)
    return default


@contextmanager
def bind_log_context(**kwargs):
    merged = get_request_context()
    for key, value in kwargs.items():
        if value is not None:
            merged[key] = value
    token = _request_context.set(merged)
    try:
        yield
    finally:
        _request_context.reset(token)


def _sanitize_request_id(raw_request_id: str) -> str:
    candidate = (raw_request_id or "").strip()
    if not candidate:
        return uuid.uuid4().hex
    if len(candidate) > 128:
        return uuid.uuid4().hex

    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.")
    if any(ch not in allowed for ch in candidate):
        return uuid.uuid4().hex
    return candidate


def _request_path(request) -> str:
    if hasattr(request, "get_full_path"):
        return request.get_full_path()
    return getattr(request, "path", "-")


def _view_name(request) -> str:
    match = getattr(request, "resolver_match", None)
    if not match:
        return "-"
    return getattr(match, "view_name", "-") or "-"


class RequestContextFilter(logging.Filter):
    """Attach request context fields to all log records."""

    def filter(self, record):
        context = _request_context.get({})
        record.request_id = getattr(record, "request_id", context.get("request_id", "-"))
        record.method = getattr(record, "method", context.get("method", "-"))
        record.path = getattr(record, "path", context.get("path", "-"))
        record.user_id = getattr(record, "user_id", context.get("user_id", "-"))
        record.view_name = getattr(record, "view_name", context.get("view_name", "-"))
        record.status_code = getattr(record, "status_code", "-")
        record.duration_ms = getattr(record, "duration_ms", "-")
        return True


class RequestObservabilityMiddleware:
    """
    Adds a request id, sets response X-Request-ID, and logs request completion.
    """

    request_logger = logging.getLogger("platform.request")
    request_id_header = "HTTP_X_REQUEST_ID"
    response_id_header = "X-Request-ID"

    def __init__(self, get_response):
        self.get_response = get_response
        self.slow_request_ms = int(
            getattr(settings, "OBSERVABILITY_SLOW_REQUEST_MS", 800)
        )

    @staticmethod
    def _user_id(request) -> str:
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return "-"
        return str(getattr(user, "pk", "-"))

    def __call__(self, request):
        request_id = _sanitize_request_id(request.META.get(self.request_id_header, ""))
        method = getattr(request, "method", "-")
        path = _request_path(request)
        view_name = _view_name(request)

        request.request_id = request_id
        token = _request_context.set(
            {
                "request_id": request_id,
                "method": method,
                "path": path,
                "user_id": self._user_id(request),
                "view_name": view_name,
            }
        )

        started_at = perf_counter()
        response = None
        status_code = 500
        try:
            response = self.get_response(request)
            status_code = getattr(response, "status_code", 500)
        except Exception:
            self.request_logger.exception(
                "request.unhandled",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "user_id": self._user_id(request),
                    "view_name": view_name,
                    "status_code": status_code,
                },
            )
            raise
        finally:
            duration_ms = round((perf_counter() - started_at) * 1000, 2)

            if duration_ms >= self.slow_request_ms:
                self.request_logger.warning(
                    "request.slow",
                    extra={
                        "request_id": request_id,
                        "method": method,
                        "path": path,
                        "user_id": self._user_id(request),
                        "view_name": _view_name(request),
                        "status_code": status_code,
                        "duration_ms": duration_ms,
                    },
                )

            self.request_logger.info(
                "request.completed",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "user_id": self._user_id(request),
                    "view_name": _view_name(request),
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                },
            )
            _request_context.reset(token)

        if response is not None:
            response[self.response_id_header] = request_id
        return response
