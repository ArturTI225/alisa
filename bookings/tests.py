from datetime import timedelta
from copy import deepcopy
import io

from django.urls import reverse
from django.utils import timezone
from django.test import override_settings, SimpleTestCase, TestCase
from django.conf import settings
from django.core.management import call_command
from rest_framework.test import APITestCase

from accounts.models import User, Address, Notification
from services.models import ServiceCategory, Service
from bookings.models import Booking, HelpRequest, VolunteerApplication
from chat.models import Conversation, ChatMessage

THROTTLE_SETTINGS = deepcopy(settings.REST_FRAMEWORK)
THROTTLE_SETTINGS["DEFAULT_THROTTLE_RATES"] = {
    **THROTTLE_SETTINGS.get("DEFAULT_THROTTLE_RATES", {}),
    "help-requests": "1/minute",
    "volunteer-applications": "30/minute",
    "user": "2/minute",
    "anon": "50/minute",
}


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

        url = reverse("v1:booking-list")
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

        url = reverse("v1:booking-list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        ids = [item["id"] for item in resp.data["results"]]
        self.assertEqual(ids[0], urgent.id)
        self.assertIn(normal.id, ids)


class BookingCreateViewTests(TestCase):
    def setUp(self):
        category = ServiceCategory.objects.create(name="Instalatii", slug="instalatii")
        self.service = Service.objects.create(
            category=category,
            name="Montaj chiuveta",
            slug="montaj-chiuveta",
        )
        self.create_url = reverse("bookings:create")

    def _payload(self, **overrides):
        payload = {
            "guest_first_name": "Anon",
            "guest_last_name": "Client",
            "guest_email": "anon@example.com",
            "guest_phone": "0700000000",
            "guest_city": "Bucuresti",
            "guest_street": "Strada Test 10",
            "guest_address_details": "Ap. 2",
            "service": self.service.id,
            "description": "Am nevoie de ajutor rapid",
            "urgency_level": Booking.UrgencyLevel.NORMAL,
            "scheduled_start": (timezone.now() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M"),
            "duration_minutes": 60,
        }
        payload.update(overrides)
        return payload

    def test_anonymous_user_can_create_booking(self):
        response = self.client.post(self.create_url, self._payload())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Booking.objects.count(), 1)

        booking = Booking.objects.select_related("client", "address").first()
        self.assertIsNotNone(booking)
        self.assertEqual(booking.client.email, "anon@example.com")
        self.assertEqual(booking.client.role, User.Roles.CLIENT)
        self.assertEqual(booking.address.city, "Bucuresti")
        self.assertEqual(booking.address.street, "Strada Test 10")

        session_user_id = self.client.session.get("_auth_user_id")
        self.assertEqual(session_user_id, str(booking.client_id))

    def test_anonymous_booking_rejects_existing_email(self):
        User.objects.create_user(
            username="existing",
            email="existing@example.com",
            password="pass12345",
            role=User.Roles.CLIENT,
        )
        response = self.client.post(
            self.create_url,
            self._payload(guest_email="existing@example.com"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Exista deja un cont cu acest email")
        self.assertEqual(Booking.objects.count(), 0)


class BookingClientDecisionWebTests(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username="client_web",
            password="pass123",
            role=User.Roles.CLIENT,
        )
        self.provider = User.objects.create_user(
            username="provider_web",
            password="pass123",
            role=User.Roles.PROVIDER,
        )
        self.category = ServiceCategory.objects.create(name="Curatenie", slug="curatenie")
        self.service = Service.objects.create(
            category=self.category,
            name="Curatenie apartament",
            slug="curatenie-apartament",
        )
        self.address = Address.objects.create(
            user=self.client_user,
            label="Acasa",
            city="Bucuresti",
            street="Strada Test 20",
        )
        self.booking = Booking.objects.create(
            client=self.client_user,
            provider=self.provider,
            service=self.service,
            address=self.address,
            description="Finalizare in asteptare",
            scheduled_start=timezone.now() - timedelta(hours=2),
            duration_minutes=60,
            status=Booking.Status.AWAITING_CLIENT,
        )

    def test_client_can_confirm_from_web_route(self):
        self.client.login(username="client_web", password="pass123")
        response = self.client.post(
            reverse("bookings:client_confirm", args=[self.booking.id])
        )
        self.assertEqual(response.status_code, 302)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.COMPLETED)
        self.assertIsNotNone(self.booking.client_confirmed_at)


class BookingAcceptChatMessageWebTests(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username="client_chat",
            password="pass123",
            role=User.Roles.CLIENT,
        )
        self.provider = User.objects.create_user(
            username="provider_chat",
            password="pass123",
            role=User.Roles.PROVIDER,
        )
        category = ServiceCategory.objects.create(name="Instalatii", slug="instalatii-2")
        service = Service.objects.create(
            category=category,
            name="Montaj baterie",
            slug="montaj-baterie",
        )
        address = Address.objects.create(
            user=self.client_user,
            label="Acasa",
            city="Bucuresti",
            street="Strada Chat 10",
        )
        self.booking = Booking.objects.create(
            client=self.client_user,
            service=service,
            address=address,
            description="Test accept + chat",
            scheduled_start=timezone.now() + timedelta(hours=2),
            duration_minutes=60,
            status=Booking.Status.PENDING,
        )

    def test_provider_accept_sends_message_to_chat(self):
        self.client.login(username="provider_chat", password="pass123")
        response = self.client.post(reverse("bookings:accept", args=[self.booking.id]))
        self.assertEqual(response.status_code, 302)

        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.CONFIRMED)
        self.assertEqual(self.booking.provider, self.provider)

        conversation = Conversation.objects.filter(booking=self.booking).first()
        self.assertIsNotNone(conversation)
        participant_ids = set(conversation.participants.values_list("id", flat=True))
        self.assertIn(self.client_user.id, participant_ids)
        self.assertIn(self.provider.id, participant_ids)

        msg = ChatMessage.objects.filter(
            conversation=conversation,
            sender=self.provider,
        ).order_by("-created_at").first()
        self.assertIsNotNone(msg)
        self.assertEqual(msg.text, "Mesterul a acceptat lucrarea.")

        self.assertTrue(
            Notification.objects.filter(
                user=self.client_user,
                type=Notification.Type.NEW_MESSAGE,
                title="Mesaj nou",
            ).exists()
        )


class HelpRequestFlowAPITests(APITestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username="client2", password="pass123", role=User.Roles.CLIENT
        )
        self.volunteer = User.objects.create_user(
            username="volunteer2", password="pass123", role=User.Roles.PROVIDER, is_verified=True
        )
        category = ServiceCategory.objects.create(name="Voluntariat", slug="voluntariat")
        self.category = category

    def test_help_request_lifecycle(self):
        # client creates help request
        self.client.login(username="client2", password="pass123")
        resp = self.client.post(
            reverse("v1:help-request-list"),
            {
                "title": "Ajutor cumpărături",
                "description": "Am nevoie de ajutor la cumpărături.",
                "city": "București",
                "region": "Sector 1",
                "urgency": HelpRequest.Urgency.LOW,
                "category_id": self.category.id,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        help_request_id = resp.data["id"]
        self.client.logout()

        # volunteer applies
        self.client.login(username="volunteer2", password="pass123")
        resp = self.client.post(
            reverse("v1:volunteer-application-list"),
            {"help_request": help_request_id, "message": "Pot ajuta."},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        app_id = resp.data["id"]
        self.client.logout()

        # client accepts
        self.client.login(username="client2", password="pass123")
        resp = self.client.post(reverse("v1:volunteer-application-accept", args=[app_id]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["status"], VolunteerApplication.Status.ACCEPTED)
        conversation = Conversation.objects.filter(help_request_id=help_request_id).first()
        self.assertIsNotNone(conversation)
        participants = set(conversation.participants.values_list("id", flat=True))
        self.assertEqual(participants, {self.client_user.id, self.volunteer.id})
        self.client.logout()

        # volunteer starts and completes
        self.client.login(username="volunteer2", password="pass123")
        start_resp = self.client.post(reverse("v1:help-request-start", args=[help_request_id]))
        self.assertEqual(start_resp.status_code, 200)
        self.assertEqual(start_resp.data["status"], HelpRequest.Status.IN_PROGRESS)

        done_resp = self.client.post(reverse("v1:help-request-complete", args=[help_request_id]))
        self.assertEqual(done_resp.status_code, 200)
        self.assertEqual(done_resp.data["status"], HelpRequest.Status.DONE)

        # volunteer can fetch certificate
        cert_resp = self.client.get(reverse("v1:help-request-certificate", args=[help_request_id]))
        self.assertEqual(cert_resp.status_code, 200)
        self.assertIn("pdf_url", cert_resp.data)

    def test_high_urgency_requires_verification(self):
        self.client.login(username="client2", password="pass123")
        resp = self.client.post(
            reverse("v1:help-request-list"),
            {
                "title": "Urgent test",
                "description": "Urgent work",
                "city": "Bucuresti",
                "region": "Sector 3",
                "urgency": HelpRequest.Urgency.HIGH,
                "category_id": self.category.id,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_help_request_review_and_review_flow(self):
        admin = User.objects.create_user(
            username="admin",
            password="pass123",
            role=User.Roles.ADMIN,
            is_staff=True,
        )
        # create help request
        self.client.login(username="client2", password="pass123")
        create_resp = self.client.post(
            reverse("v1:help-request-list"),
            {
                "title": "Ajutor cumparaturi 2",
                "description": "Detalii suplimentare.",
                "city": "Bucuresti",
                "region": "Sector 2",
                "urgency": HelpRequest.Urgency.LOW,
                "category_id": self.category.id,
            },
            format="json",
        )
        self.assertEqual(create_resp.status_code, 201)
        help_request_id = create_resp.data["id"]
        self.client.logout()

        # moderation review + approve
        self.client.login(username="admin", password="pass123")
        to_review = self.client.post(reverse("v1:help-request-send-to-review", args=[help_request_id]))
        self.assertEqual(to_review.status_code, 200)
        approve = self.client.post(reverse("v1:help-request-approve", args=[help_request_id]))
        self.assertEqual(approve.status_code, 200)
        self.assertEqual(approve.data["status"], HelpRequest.Status.OPEN)
        self.client.logout()

        # volunteer applies
        self.client.login(username="volunteer2", password="pass123")
        app_resp = self.client.post(
            reverse("v1:volunteer-application-list"),
            {"help_request": help_request_id, "message": "Pot ajuta rapid."},
            format="json",
        )
        self.assertEqual(app_resp.status_code, 201)
        app_id = app_resp.data["id"]
        self.client.logout()

        # client accepts
        self.client.login(username="client2", password="pass123")
        acc_resp = self.client.post(reverse("v1:volunteer-application-accept", args=[app_id]))
        self.assertEqual(acc_resp.status_code, 200)
        self.client.logout()

        # volunteer starts and completes
        self.client.login(username="volunteer2", password="pass123")
        self.assertEqual(self.client.post(reverse("v1:help-request-start", args=[help_request_id])).status_code, 200)
        self.assertEqual(self.client.post(reverse("v1:help-request-complete", args=[help_request_id])).status_code, 200)
        cert_resp = self.client.get(reverse("v1:help-request-certificate", args=[help_request_id]))
        self.assertEqual(cert_resp.status_code, 200)
        self.client.logout()

        # requester leaves review linked to help request
        self.client.login(username="client2", password="pass123")
        review_resp = self.client.post(
            reverse("v1:review-list"),
            {
                "to_user_id": self.volunteer.id,
                "help_request_id": help_request_id,
                "rating": 5,
                "comment": "Mulțumesc pentru ajutor!",
            },
            format="json",
        )
        self.assertEqual(review_resp.status_code, 201)
        self.assertEqual(review_resp.data["help_request"], help_request_id)
        self.assertEqual(review_resp.data["to_user"]["id"], self.volunteer.id)


@override_settings(REST_FRAMEWORK=THROTTLE_SETTINGS)
class AbusePreventionTests(APITestCase):
    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        self.client_user = User.objects.create_user(
            username="client_t",
            password="pass123",
            role=User.Roles.CLIENT,
        )
        self.volunteer = User.objects.create_user(
            username="volunteer_t",
            password="pass123",
            role=User.Roles.PROVIDER,
            is_verified=True,
        )
        self.blocked_client = User.objects.create_user(
            username="blocked_client",
            password="pass123",
            role=User.Roles.CLIENT,
            is_blocked=True,
        )
        self.blocked_volunteer = User.objects.create_user(
            username="blocked_volunteer",
            password="pass123",
            role=User.Roles.PROVIDER,
            is_verified=True,
            is_blocked=True,
        )
        category = ServiceCategory.objects.create(name="General", slug="general")
        self.category = category

    def test_help_request_throttle_scope(self):
        from django.conf import settings
        from bookings.views import HelpRequestThrottle

        self.assertEqual(settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["help-requests"], "1/minute")
        self.assertEqual(HelpRequestThrottle().get_rate(), "1/minute")
        self.client.login(username="client_t", password="pass123")
        payload = {
            "title": "Test throttle",
            "description": "Descriere scurta",
            "city": "Bucuresti",
            "region": "Sector 1",
            "urgency": HelpRequest.Urgency.LOW,
            "category_id": self.category.id,
        }
        first = self.client.post(reverse("v1:help-request-list"), payload, format="json")
        self.assertEqual(first.status_code, 201, first.data)
        second = self.client.post(reverse("v1:help-request-list"), payload, format="json")
        self.assertEqual(second.status_code, 429, second.data)

    def test_blocked_user_cannot_create_or_apply(self):
        # create an open help request by a normal client
        self.client.login(username="client_t", password="pass123")
        resp = self.client.post(
            reverse("v1:help-request-list"),
            {
                "title": "Aplicatii blocate",
                "description": "Descriere suficient de lunga",
                "city": "Bucuresti",
                "region": "Sector 1",
                "urgency": HelpRequest.Urgency.LOW,
                "category_id": self.category.id,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        help_request_id = resp.data["id"]
        self.client.logout()

        # blocked client cannot create
        self.client.login(username="blocked_client", password="pass123")
        blocked_create = self.client.post(
            reverse("v1:help-request-list"),
            {
                "title": "Nu ar trebui sa se creeze",
                "description": "Test",
                "city": "Bucuresti",
                "region": "Sector 1",
                "urgency": HelpRequest.Urgency.LOW,
                "category_id": self.category.id,
            },
            format="json",
        )
        self.assertEqual(blocked_create.status_code, 403)
        self.client.logout()

        # blocked volunteer cannot apply
        self.client.login(username="blocked_volunteer", password="pass123")
        apply_resp = self.client.post(
            reverse("v1:volunteer-application-list"),
            {"help_request": help_request_id, "message": "Nu ar trebui sa fie permis."},
            format="json",
        )
        self.assertEqual(apply_resp.status_code, 403)
        self.client.logout()


class MigrationSmokeTests(SimpleTestCase):
    databases = {"default"}

    def test_no_pending_migrations(self):
        out = io.StringIO()
        try:
            call_command("makemigrations", "--check", "--dry-run", stdout=out, stderr=out)
        except SystemExit as exc:
            if exc.code != 0:
                self.fail(f"Pending migrations detected or makemigrations failed: {out.getvalue()}")
