from django.urls import path

from .views import (
    ApplicationsView,
    ClientAcceptApplicationView,
    ClientHelpRequestCreateView,
    FAQView,
    HomePageView,
    HowItWorksView,
    ProviderApplyView,
    ReviewsView,
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
    path("applications/", ApplicationsView.as_view(), name="applications"),
    path("reviews/", ReviewsView.as_view(), name="reviews"),
    path("cum-functioneaza/", HowItWorksView.as_view(), name="how_it_works"),
    path("faq/", FAQView.as_view(), name="faq"),
    path("devino-membru/", ProviderApplyView.as_view(), name="apply"),
]
