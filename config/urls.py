from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("services/", include("services.urls")),
    path("bookings/", include("bookings.urls")),
    path("chat/", include("chat.urls", namespace="chat")),
    path("api/", include("config.api_router")),
    path("", include("pages.urls")),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )
