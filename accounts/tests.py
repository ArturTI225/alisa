from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from accounts.models import (
    Address,
    Badge,
    FavoriteProvider,
    FavoriteService,
    Notification,
    NotificationPreference,
    User,
)
from accounts.utils import notify_user
from config.observability import bind_log_context
from services.models import Service, ServiceCategory


class SignupFlowTests(TestCase):
    def test_signup_page_exposes_client_and_worker_role_choices(self):
        response = self.client.get(reverse("accounts:signup"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="client"')
        self.assertContains(response, 'value="provider"')
        self.assertContains(response, "Worker")
        self.assertContains(response, 'class="ff__label"', html=False)
        self.assertContains(response, "Confirma parola")

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


class LoginTemplateTests(TestCase):
    def test_login_page_uses_shared_form_field_component(self):
        response = self.client.get(reverse("accounts:login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Continua cu datele tale")
        self.assertContains(response, 'class="ff__label"', html=False)
        self.assertContains(response, 'name="username"', html=False)
        self.assertContains(response, 'name="password"', html=False)


class ProfileViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="profile_user",
            password="StrongPass123!",
            role=User.Roles.CLIENT,
            city="Chisinau",
            phone="0700000000",
        )
        self.provider = User.objects.create_user(
            username="profile_provider",
            password="StrongPass123!",
            role=User.Roles.PROVIDER,
            city="Balti",
        )
        self.category = ServiceCategory.objects.create(
            name="Instalatii profil",
            slug="instalatii-profil",
        )
        self.service = Service.objects.create(
            category=self.category,
            name="Montaj lampa",
            slug="montaj-lampa",
        )

    def test_profile_page_surfaces_counts_and_saved_sections(self):
        Address.objects.create(
            user=self.user,
            label="Acasa",
            city="Chisinau",
            street="Strada Profil 1",
            is_default=True,
        )
        FavoriteService.objects.create(user=self.user, service=self.service)
        FavoriteProvider.objects.create(user=self.user, provider=self.provider)
        Notification.objects.create(
            user=self.user,
            title="Mesaj nou",
            body="Ai primit un mesaj nou.",
            is_read=False,
        )

        self.client.login(username=self.user.username, password="StrongPass123!")
        response = self.client.get(reverse("accounts:profile"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Centru cont")
        self.assertContains(response, "Notificari necitite: 1")
        self.assertContains(response, "Locuri folosite frecvent")
        self.assertContains(response, "Montaj lampa")
        self.assertContains(response, "Balti")

    def test_provider_profile_page_shows_skills_and_badges(self):
        badge = Badge.objects.create(name="Comunitate", description="Test")
        self.provider.provider_profile.experience_years = 4
        self.provider.provider_profile.verification_status = "verified"
        self.provider.provider_profile.verification_note = "Actele sunt validate."
        self.provider.provider_profile.save(
            update_fields=["experience_years", "verification_status", "verification_note"]
        )
        self.provider.provider_profile.skills.add(self.service)
        self.provider.provider_profile.badges.add(badge)

        self.client.login(username=self.provider.username, password="StrongPass123!")
        response = self.client.get(reverse("accounts:profile"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Panou rapid pentru activitatea de prestator")
        self.assertContains(response, "Montaj lampa")
        self.assertContains(response, "Comunitate")
        self.assertContains(response, "Actele sunt validate.")


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


class NotificationPreferenceFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="pref_user",
            password="StrongPass123!",
            role=User.Roles.CLIENT,
        )

    def test_preferences_page_renders_breadcrumbs_and_sound_toggle(self):
        self.client.login(username=self.user.username, password="StrongPass123!")

        response = self.client.get(reverse("accounts:notification_preferences"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'aria-label="Navigare secundara"', html=False)
        self.assertContains(response, "Sunet pentru notificarile live")
        self.assertContains(response, 'data-notification-sound-enabled="false"', html=False)

    def test_preferences_form_can_enable_notification_sound(self):
        self.client.login(username=self.user.username, password="StrongPass123!")

        response = self.client.post(
            reverse("accounts:notification_preferences"),
            {
                "booking_updates": "on",
                "disputes": "on",
                "recurring": "on",
                "chat_messages": "on",
                "bids": "on",
                "urgent_ads": "on",
                "reviews": "on",
                "in_app_sound": "on",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        pref = NotificationPreference.objects.get(user=self.user)
        self.assertTrue(pref.in_app_sound)

        notifications_response = self.client.get(reverse("accounts:notifications"))
        self.assertContains(
            notifications_response,
            'data-notification-sound-enabled="true"',
            html=False,
        )


class NotificationObservabilityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="notif_obs_user",
            password="StrongPass123!",
            role=User.Roles.CLIENT,
        )

    @patch("accounts.utils._push_ws")
    def test_notify_user_payload_includes_explicit_request_id(self, push_ws_mock):
        notify_user(
            user=self.user,
            notif_type=Notification.Type.GENERAL,
            title="Titlu",
            body="Mesaj",
            request_id="notif-explicit-123",
        )

        self.assertTrue(push_ws_mock.called)
        payload = push_ws_mock.call_args.args[1]
        self.assertEqual(payload.get("request_id"), "notif-explicit-123")

    @patch("accounts.utils._push_ws")
    def test_notify_user_payload_includes_context_request_id(self, push_ws_mock):
        with bind_log_context(request_id="notif-context-456"):
            notify_user(
                user=self.user,
                notif_type=Notification.Type.GENERAL,
                title="Titlu",
                body="Mesaj",
            )

        self.assertTrue(push_ws_mock.called)
        payload = push_ws_mock.call_args.args[1]
        self.assertEqual(payload.get("request_id"), "notif-context-456")
