from django.urls import path
from django.views.generic import RedirectView

from .views import (
    ClientAcceptApplicationView,
    ClientHelpRequestCreateView,
    FAQView,
    HomePageView,
    HowItWorksView,
    ProviderApplyView,
    WorkerApplyHelpRequestView,
    WorkerStartHelpRequestView,
)

app_name = "pages"

urlpatterns = [
    path("", HomePageView.as_view(), name="home"),
    path(
        "help-requests/create/",
        ClientHelpRequestCreateView.as_view(),
        name="help_request_create",
    ),
    path(
        "help-requests/<int:pk>/apply/",
        WorkerApplyHelpRequestView.as_view(),
        name="help_request_apply",
    ),
    path(
        "help-requests/<int:pk>/start/",
        WorkerStartHelpRequestView.as_view(),
        name="help_request_start",
    ),
    path(
        "applications/<int:pk>/accept/",
        ClientAcceptApplicationView.as_view(),
        name="application_accept",
    ),
    path("cum-functioneaza/", HowItWorksView.as_view(), name="how_it_works"),
    path("faq/", FAQView.as_view(), name="faq"),
    path("devino-membru/", ProviderApplyView.as_view(), name="apply"),
    path(
        "devino-sot-la-ora/",
        RedirectView.as_view(url="/devino-membru/", permanent=True),
        name="apply_legacy_redirect",
    ),
]
