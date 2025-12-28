from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import User, Address
from services.models import ServiceCategory, Service
from bookings.models import Booking


class BookingUrgencyAPITests(APITestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username="client", password="pass123", role=User.Roles.CLIENT
        )
        self.provider = User.objects.create_user(
            username="provider",
            password="pass123",
            role=User.Roles.PROVIDER,
            city="Bucharest",
        )
        self.address = Address.objects.create(
            user=self.client_user,
            label="Casa",
            city="Bucharest",
            street="Strada Test 1",
        )
        category = ServiceCategory.objects.create(name="Electric", slug="electric")
        self.service = Service.objects.create(
            category=category,
            name="Montaj priza",
            slug="montaj-priza",
            base_price=100,
        )
        self.client.login(username="client", password="pass123")

    def test_filter_by_urgent_flag(self):
        urgent = Booking.objects.create(
            client=self.client_user,
            provider=self.provider,
            service=self.service,
            address=self.address,
            description="Urgent job",
            scheduled_start=timezone.now(),
            duration_minutes=60,
            is_urgent=True,
            urgency_level=Booking.UrgencyLevel.CRITICAL,
        )
        Booking.objects.create(
            client=self.client_user,
            provider=self.provider,
            service=self.service,
            address=self.address,
            description="Normal job",
            scheduled_start=timezone.now() + timedelta(hours=1),
            duration_minutes=60,
            is_urgent=False,
        )

        url = reverse("booking-list")
        resp = self.client.get(url, {"is_urgent": "true"})
        self.assertEqual(resp.status_code, 200)
        ids = [item["id"] for item in resp.data["results"]]
        self.assertEqual(ids, [urgent.id])

    def test_ordering_prioritizes_urgent(self):
        normal = Booking.objects.create(
            client=self.client_user,
            provider=self.provider,
            service=self.service,
            address=self.address,
            description="Normal job",
            scheduled_start=timezone.now(),
            duration_minutes=60,
            is_urgent=False,
        )
        urgent = Booking.objects.create(
            client=self.client_user,
            provider=self.provider,
            service=self.service,
            address=self.address,
            description="Urgent job",
            scheduled_start=timezone.now() + timedelta(hours=2),
            duration_minutes=60,
            is_urgent=True,
            urgency_level=Booking.UrgencyLevel.HIGH,
        )

        url = reverse("booking-list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        ids = [item["id"] for item in resp.data["results"]]
        self.assertEqual(ids[0], urgent.id)
        self.assertIn(normal.id, ids)

# Create your tests here.
