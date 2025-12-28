from django.urls import reverse
from rest_framework.test import APITestCase

from accounts.models import User, Notification
from ads.models import Ad
from services.models import ServiceCategory


class ConversationAPITests(APITestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username="client",
            password="pass123",
            role=User.Roles.CLIENT,
            city="Bucharest",
        )
        self.provider = User.objects.create_user(
            username="provider",
            password="pass123",
            role=User.Roles.PROVIDER,
            city="Bucharest",
        )
        category = ServiceCategory.objects.create(name="Electric", slug="electric")
        self.ad = Ad.objects.create(
            client=self.client_user,
            title="Reparatie",
            description="Lampa nu merge",
            category=category,
            city="Bucharest",
        )
        self.client.login(username="client", password="pass123")

    def test_create_conversation_and_message(self):
        convo_url = reverse("conversation-list")
        resp = self.client.post(
            convo_url,
            {"ad": self.ad.id, "participant_ids": [self.provider.id]},
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        convo_id = resp.data["id"]
        msg_url = reverse("chatmessage-list")
        resp_msg = self.client.post(
            msg_url,
            {"conversation": convo_id, "text": "Salut"},
            format="json",
        )
        self.assertEqual(resp_msg.status_code, 201, resp_msg.data)
        # provider gets notification
        self.client.logout()
        self.client.login(username="provider", password="pass123")
        notifs = Notification.objects.filter(user=self.provider, type=Notification.Type.NEW_MESSAGE)
        self.assertTrue(notifs.exists())
