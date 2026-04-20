from time import perf_counter
import uuid

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.utils import timezone


def _check_database() -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()


def _check_cache() -> None:
    key = f"healthz:{uuid.uuid4().hex}"
    value = uuid.uuid4().hex
    cache.set(key, value, timeout=10)
    cached = cache.get(key)
    cache.delete(key)
    if cached != value:
        raise RuntimeError("cache round-trip mismatch")


def _check_channels() -> None:
    layer = get_channel_layer()
    if layer is None:
        raise RuntimeError("channel layer unavailable")

    channel_name = async_to_sync(layer.new_channel)("healthz.")
    payload = {"type": "health.ping", "value": "ok"}
    async_to_sync(layer.send)(channel_name, payload)
    received = async_to_sync(layer.receive)(channel_name)
    if not isinstance(received, dict) or received.get("type") != "health.ping":
        raise RuntimeError("channel layer round-trip mismatch")


def _run_probe(check_func):
    started_at = perf_counter()
    try:
        check_func()
        return {
            "status": "ok",
            "latency_ms": round((perf_counter() - started_at) * 1000, 2),
        }
    except Exception as exc:  # noqa: BLE001 - health endpoint should report probe failures
        return {
            "status": "error",
            "latency_ms": round((perf_counter() - started_at) * 1000, 2),
            "error": str(exc),
        }


def health_view(request):
    components = {
        "database": _run_probe(_check_database),
        "cache": _run_probe(_check_cache),
        "channels": _run_probe(_check_channels),
    }
    all_ok = all(item["status"] == "ok" for item in components.values())

    payload = {
        "status": "ok" if all_ok else "degraded",
        "timestamp": timezone.now().isoformat(),
        "components": components,
    }

    request_id = getattr(request, "request_id", "")
    if request_id:
        payload["request_id"] = request_id

    return JsonResponse(payload, status=200 if all_ok else 503)
