from django.urls import path

from .views import FAQView, HomePageView, HowItWorksView, ProviderApplyView

app_name = "pages"

urlpatterns = [
    path("", HomePageView.as_view(), name="home"),
    path("cum-functioneaza/", HowItWorksView.as_view(), name="how_it_works"),
    path("faq/", FAQView.as_view(), name="faq"),
    path("devino-sot-la-ora/", ProviderApplyView.as_view(), name="apply"),
]
