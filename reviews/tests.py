from django.urls import reverse
from rest_framework.test import APITestCase

from accounts.models import User
from ads.models import Ad
from services.models import ServiceCategory
from reviews.models import Review


class ReviewRatingTests(APITestCase):
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
        )
        category = ServiceCategory.objects.create(name="Electric", slug="electric")
        self.ad = Ad.objects.create(
            client=self.client_user,
            title="Montaj",
            description="Instalare",
            category=category,
            city="Bucharest",
            assigned_craftsman=self.provider,
            status=Ad.Status.IN_PROGRESS,
        )
        self.client.login(username="client", password="pass123")

    def test_review_updates_rating(self):
        url = reverse("review-list")
        resp = self.client.post(
            url,
            {
                "to_user_id": self.provider.id,
                "ad": self.ad.id,
                "rating": 4,
                "comment": "Bun",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        self.provider.refresh_from_db()
        self.assertEqual(float(self.provider.rating_avg), 4.0)
        self.assertEqual(self.provider.rating_count, 1)
        # second review lowers average
        Review.objects.create(
            from_user=self.client_user, to_user=self.provider, ad=self.ad, rating=2
        )
        self.provider.refresh_from_db()
        self.assertEqual(self.provider.rating_count, 2)
        self.assertAlmostEqual(float(self.provider.rating_avg), 3.0, places=1)
