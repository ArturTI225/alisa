from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from rest_framework.schemas import get_schema_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("services/", include("services.urls")),
    path("bookings/", include("bookings.urls")),
    path("chat/", include("chat.urls", namespace="chat")),
    path("api/v1/", include(("config.api_router", "api"), namespace="v1")),
    # temporary compatibility path
    path("api/", include("config.api_router")),
    path(
        "api/v1/schema/",
        get_schema_view(
            title="ALISA API",
            description="Social, non-commercial volunteer platform API schema",
            version="1.0",
        ),
        name="api-schema",
    ),
    path("health/", lambda request: JsonResponse({"status": "ok"})),
    path("", include("pages.urls")),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )
