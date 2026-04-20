from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Address, User
from bookings.models import Booking, HelpRequest, VolunteerApplication
from chat.models import Conversation
from services.models import Service, ServiceCategory


class RoleBasedHomeTests(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username="client_home",
            password="pass123",
            role=User.Roles.CLIENT,
            is_verified=True,
        )
        self.worker = User.objects.create_user(
            username="worker_home",
            password="pass123",
            role=User.Roles.PROVIDER,
        )
        self.category = ServiceCategory.objects.create(
            name="Electric",
            slug="electric-home",
        )
        self.service = Service.objects.create(
            category=self.category,
            name="Reparatie priza",
            slug="reparatie-priza-home",
        )
        self.client_address = Address.objects.create(
            user=self.client_user,
            label="Acasa",
            city="Chisinau",
            street="Strada Test 1",
            details="Bloc A",
        )

    def test_client_uses_client_home_template(self):
        self.client.login(username="client_home", password="pass123")
        response = self.client.get(reverse("pages:home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/home_client.html")

    def test_worker_uses_worker_home_template(self):
        self.client.login(username="worker_home", password="pass123")
        response = self.client.get(reverse("pages:home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/home_worker.html")

    def test_client_can_create_help_request_from_home_form(self):
        self.client.login(username="client_home", password="pass123")
        response = self.client.post(
            reverse("pages:help_request_create"),
            data={
                "category": self.category.id,
                "description": "S-a ars siguranta si nu mai merge curentul.",
                "urgency": HelpRequest.Urgency.MEDIUM,
                "city": "Chisinau",
                "region": "Centru",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            HelpRequest.objects.filter(
                created_by=self.client_user, category=self.category
            ).exists()
        )

    def test_accept_application_creates_chat_and_worker_can_start(self):
        help_request = HelpRequest.objects.create(
            created_by=self.client_user,
            title="Problema electrica",
            description="Scurt circuit in panou.",
            category=self.category,
            city="Chisinau",
            urgency=HelpRequest.Urgency.MEDIUM,
            status=HelpRequest.Status.OPEN,
            status_history=[],
        )
        application = VolunteerApplication.objects.create(
            help_request=help_request,
            volunteer=self.worker,
            status=VolunteerApplication.Status.PENDING,
            message="Pot veni in 30 minute.",
        )

        self.client.login(username="client_home", password="pass123")
        accept_response = self.client.post(
            reverse("pages:application_accept", args=[application.id])
        )
        self.assertEqual(accept_response.status_code, 302)

        help_request.refresh_from_db()
        application.refresh_from_db()
        self.assertEqual(application.status, VolunteerApplication.Status.ACCEPTED)
        self.assertEqual(help_request.status, HelpRequest.Status.MATCHED)
        self.assertEqual(help_request.matched_volunteer_id, self.worker.id)

        conversation = Conversation.objects.get(help_request=help_request)
        participant_ids = set(conversation.participants.values_list("id", flat=True))
        self.assertEqual(
            participant_ids,
            {self.client_user.id, self.worker.id},
        )

        self.client.logout()
        self.client.login(username="worker_home", password="pass123")
        start_response = self.client.post(
            reverse("pages:help_request_start", args=[help_request.id])
        )
        self.assertEqual(start_response.status_code, 302)
        help_request.refresh_from_db()
        self.assertEqual(help_request.status, HelpRequest.Status.IN_PROGRESS)

    def test_worker_dashboard_shows_own_client_requests(self):
        own_request = HelpRequest.objects.create(
            created_by=self.worker,
            title="Cerere personala",
            description="Am nevoie de ajutor la reparatia usii.",
            category=self.category,
            city="Chisinau",
            urgency=HelpRequest.Urgency.LOW,
            status=HelpRequest.Status.OPEN,
            status_history=[],
        )

        self.client.login(username="worker_home", password="pass123")
        response = self.client.get(reverse("pages:home"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/home_worker.html")
        self.assertIn("my_client_requests", response.context)
        self.assertIn(own_request, response.context["my_client_requests"])
        self.assertNotIn(own_request, response.context["open_requests"])
        self.assertContains(response, "Cererile mele (ca solicitant)")

    def test_worker_dashboard_shows_open_booking_requests(self):
        booking = Booking.objects.create(
            client=self.client_user,
            service=self.service,
            address=self.client_address,
            description="Prizele nu functioneaza in bucatarie.",
            scheduled_start=timezone.now() + timedelta(days=1),
            duration_minutes=90,
            status=Booking.Status.PENDING,
            provider=None,
        )

        self.client.login(username="worker_home", password="pass123")
        response = self.client.get(reverse("pages:home"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("open_bookings", response.context)
        self.assertIn(booking, response.context["open_bookings"])
        self.assertContains(response, f"Cerere #{booking.id}")

    def test_home_includes_phase_four_accessibility_shell(self):
        self.client.login(username="client_home", password="pass123")

        response = self.client.get(reverse("pages:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sari direct la continut")
        self.assertContains(response, 'id="command-palette"', html=False)
        self.assertContains(response, 'data-open-command-palette', html=False)
        self.assertContains(response, 'aria-current="page"', html=False)
