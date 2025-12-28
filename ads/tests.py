from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import User
from services.models import ServiceCategory
from ads.models import Ad, Offer


class AdOfferAPITests(APITestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username="client",
            password="pass123",
            role=User.Roles.CLIENT,
        )
        self.provider = User.objects.create_user(
            username="provider",
            password="pass123",
            role=User.Roles.PROVIDER,
            city="Bucharest",
        )
        self.category = ServiceCategory.objects.create(
            name="Electric", slug="electric"
        )
        self.client.login(username="client", password="pass123")

    def test_create_ad_and_filter_urgent(self):
        url = reverse("ad-list")
        payload = {
            "title": "Montaj priza",
            "description": "Urgent, apa in perete",
            "category_id": self.category.id,
            "city": "Bucharest",
            "budget_min": "100",
            "budget_max": "200",
            "is_urgent": True,
            "deadline": (timezone.now() + timedelta(days=1)).isoformat(),
        }
        resp = self.client.post(url, payload, format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        list_resp = self.client.get(url, {"is_urgent": "true"})
        self.assertEqual(list_resp.status_code, 200)
        ids = [row["id"] for row in list_resp.data["results"]]
        self.assertEqual(len(ids), 1)

    def test_offer_flow_accept(self):
        ad = Ad.objects.create(
            client=self.client_user,
            title="Reparatie",
            description="Schimba robinet",
            category=self.category,
            city="Bucharest",
            is_urgent=False,
        )
        self.client.logout()
        self.client.login(username="provider", password="pass123")
        offer_url = reverse("offer-list")
        resp = self.client.post(
            offer_url,
            {"ad": ad.id, "message": "Pot veni azi", "proposed_price": "150"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        offer_id = resp.data["id"]

        self.client.logout()
        self.client.login(username="client", password="pass123")
        accept_url = reverse("offer-accept", args=[offer_id])
        accept_resp = self.client.post(accept_url)
        self.assertEqual(accept_resp.status_code, 200, accept_resp.data)
        offer = Offer.objects.get(pk=offer_id)
        ad.refresh_from_db()
        self.assertEqual(offer.status, Offer.Status.ACCEPTED)
        self.assertEqual(ad.assigned_craftsman, self.provider)
        self.assertEqual(ad.status, Ad.Status.IN_PROGRESS)
