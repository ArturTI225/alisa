from django.test import TestCase
from django.urls import reverse

from accounts.models import User


class SignupFlowTests(TestCase):
    def test_signup_page_exposes_client_and_worker_role_choices(self):
        response = self.client.get(reverse("accounts:signup"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="client"')
        self.assertContains(response, 'value="provider"')
        self.assertContains(response, "Worker")

    def test_signup_can_create_worker_account(self):
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "username": "worker_user",
                "email": "worker@example.com",
                "first_name": "Test",
                "last_name": "Worker",
                "phone": "0700000000",
                "city": "Chisinau",
                "role": User.Roles.PROVIDER,
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="worker_user")
        self.assertEqual(user.role, User.Roles.PROVIDER)
        self.assertTrue(hasattr(user, "provider_profile"))


class LogoutFlowTests(TestCase):
    def test_logout_via_post_clears_session(self):
        user = User.objects.create_user(
            username="logout_user",
            password="StrongPass123!",
            role=User.Roles.CLIENT,
        )
        self.client.login(username=user.username, password="StrongPass123!")
        response = self.client.post(reverse("accounts:logout"), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
