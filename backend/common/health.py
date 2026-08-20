from django.conf import settings
from django.db import connections
from redis import Redis
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


def check_database() -> None:
    with connections["default"].cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()


def check_redis() -> None:
    client = Redis.from_url(
        settings.REDIS_URL,
        socket_connect_timeout=1,
        socket_timeout=1,
    )
    try:
        if client.ping() is not True:
            raise ConnectionError("Redis PING failed.")
    finally:
        client.close()


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def health_check(request):
    try:
        check_database()
        check_redis()
    except Exception:  # noqa: BLE001 - readiness must map every dependency failure to 503.
        return Response(
            {"status": "unavailable"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return Response(
        {
            "status": "ok",
            "dependencies": {"database": "ok", "redis": "ok"},
        }
    )
