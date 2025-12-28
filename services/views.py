from django.views import generic
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from rest_framework import filters, permissions, viewsets

from .models import Service, ServiceCategory
from .serializers import ServiceCategorySerializer, ServiceSerializer


class ServiceListView(generic.ListView):
    template_name = "services/list.html"
    model = Service
    context_object_name = "services"
    paginate_by = 9

    def get_queryset(self):
        qs = Service.objects.filter(is_active=True).select_related("category")
        category = self.request.GET.get("category")
        city = self.request.GET.get("city")
        if category:
            qs = qs.filter(category__slug=category)
        if city:
            qs = qs.filter(providers__city__icontains=city).distinct()
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categories"] = ServiceCategory.objects.filter(is_active=True)
        return ctx


class ServiceCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ServiceCategory.objects.filter(is_active=True)
    serializer_class = ServiceCategorySerializer
    permission_classes = [permissions.AllowAny]


class ServiceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Service.objects.filter(is_active=True).select_related("category")
    serializer_class = ServiceSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["base_price", "duration_estimate_minutes"]
